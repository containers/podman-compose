# SPDX-License-Identifier: GPL-2.0

import os
import socket
import struct
import threading
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin

expected_lines = [
    "default: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFYQvN9a+toIB6jSs4zY7FMapZnHt80EKCUr/WhLwUum",
    "id1: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFYQvN9a+toIB6jSs4zY7FMapZnHt80EKCUr/WhLwUum",
    "id2: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFYQvN9a+toIB6jSs4zY7FMapZnHt80EKCUr/WhLwUum",
]


class TestBuildSsh(unittest.TestCase, RunSubprocessMixin):
    def test_build_ssh(self):
        """The build context can contain the ssh authentications that the image builder should
        use during image build. They can be either an array or a map.
        """

        compose_path = os.path.join(test_path(), "build_ssh/docker-compose.yml")
        sock_path = os.path.join(test_path(), "build_ssh/agent_dummy.sock")
        private_key_file = os.path.join(test_path(), "build_ssh/id_ed25519_dummy")

        agent = MockSSHAgent(private_key_file)

        try:
            # Set SSH_AUTH_SOCK because `default` expects it
            os.environ['SSH_AUTH_SOCK'] = sock_path

            # Start a mock SSH agent server
            agent.start_agent(sock_path)

            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "build",
                "test_build_ssh_map",
                "test_build_ssh_array",
            ])

            for test_image in [
                "test_build_ssh_map",
                "test_build_ssh_array",
            ]:
                out, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_path,
                    "run",
                    "--rm",
                    test_image,
                ])

                out = out.decode('utf-8')

                # Check if all lines are contained in the output
                self.assertTrue(
                    all(line in out for line in expected_lines),
                    f"Incorrect output for image {test_image}",
                )

        finally:
            # Now we send the stop command to gracefully shut down the server
            agent.stop_agent()

            if os.path.exists(sock_path):
                os.remove(sock_path)

            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "my-alpine-build-ssh-map",
                "my-alpine-build-ssh-array",
            ])


# SSH agent message types
SSH_AGENTC_REQUEST_IDENTITIES = 11
SSH_AGENT_IDENTITIES_ANSWER = 12
SSH_AGENT_FAILURE = 5
STOP_REQUEST = 0xFF


class MockSSHAgent:
    def __init__(self, private_key_path):
        self.sock_path = None
        self.server_sock = None
        self.running = threading.Event()
        self.keys = [self._load_ed25519_private_key(private_key_path)]
        self.agent_thread = None  # Thread to run the agent

    def _load_ed25519_private_key(self, private_key_path):
        """Load ED25519 private key from an OpenSSH private key file."""
        with open(private_key_path, 'rb') as key_file:
            private_key = serialization.load_ssh_private_key(key_file.read(), password=None)

        # Ensure it's an Ed25519 key
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("Invalid key type, expected ED25519 private key.")

        # Get the public key corresponding to the private key
        public_key = private_key.public_key()

        # Serialize the public key to the OpenSSH format
        public_key_blob = public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        # SSH key type "ssh-ed25519"
        key_type = b"ssh-ed25519"

        # Build the key blob (public key part for the agent)
        key_blob_full = (
            struct.pack(">I", len(key_type))
            + key_type  # Key type length + type
            + struct.pack(">I", len(public_key_blob))
            + public_key_blob  # Public key length + key blob
        )

        # Comment (empty)
        comment = ""

        return ("ssh-ed25519", key_blob_full, comment)

    def start_agent(self, sock_path):
        """Start the mock SSH agent and create a Unix domain socket."""
        self.sock_path = sock_path
        if os.path.exists(self.sock_path):
            os.remove(self.sock_path)

        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.bind(self.sock_path)
        self.server_sock.listen(5)

        os.environ['SSH_AUTH_SOCK'] = self.sock_path

        self.running.set()  # Set the running event

        # Start a thread to accept client connections
        self.agent_thread = threading.Thread(target=self._accept_connections, daemon=True)
        self.agent_thread.start()

    def _accept_connections(self):
        """Accept and handle incoming connections."""
        while self.running.is_set():
            try:
                client_sock, _ = self.server_sock.accept()
                self._handle_client(client_sock)
            except Exception as e:
                print(f"Error accepting connection: {e}")

    def _handle_client(self, client_sock):
        """Handle a single client request (like ssh-add)."""
        try:
            # Read the message length (first 4 bytes)
            length_message = client_sock.recv(4)
            if not length_message:
                raise "no length message received"

            msg_len = struct.unpack(">I", length_message)[0]

            request_message = client_sock.recv(msg_len)

            # Check for STOP_REQUEST
            if request_message[0] == STOP_REQUEST:
                client_sock.close()
                self.running.clear()  # Stop accepting connections
                return

            # Check for SSH_AGENTC_REQUEST_IDENTITIES
            if request_message[0] == SSH_AGENTC_REQUEST_IDENTITIES:
                response = self._mock_list_keys_response()
                client_sock.sendall(response)
            else:
                print("Message not recognized")
                # Send failure if the message type is not recognized
                response = struct.pack(">I", 1) + struct.pack(">B", SSH_AGENT_FAILURE)
                client_sock.sendall(response)

        except socket.error:
            print("Client socket error.")
            pass  # You can handle specific errors here if needed
        finally:
            client_sock.close()  # Ensure the client socket is closed

    def _mock_list_keys_response(self):
        """Create a mock response for ssh-add -l, listing keys."""

        # Start building the response
        response = struct.pack(">B", SSH_AGENT_IDENTITIES_ANSWER)  # Message type

        # Number of keys
        response += struct.pack(">I", len(self.keys))

        # For each key, append key blob and comment
        for key_type, key_blob, comment in self.keys:
            # Key blob length and content
            response += struct.pack(">I", len(key_blob)) + key_blob

            # Comment length and content
            comment_encoded = comment.encode()
            response += struct.pack(">I", len(comment_encoded)) + comment_encoded

        # Prefix the entire response with the total message length
        response = struct.pack(">I", len(response)) + response

        return response

    def stop_agent(self):
        """Stop the mock SSH agent."""
        if self.running.is_set():  # First check if the agent is running
            # Create a temporary connection to send the stop command
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client_sock:
                client_sock.connect(self.sock_path)  # Connect to the server

                stop_command = struct.pack(
                    ">B", STOP_REQUEST
                )  # Pack the stop command as a single byte

                # Send the message length first
                message_length = struct.pack(">I", len(stop_command))
                client_sock.sendall(message_length)  # Send the length first

                client_sock.sendall(stop_command)  # Send the stop command

            self.running.clear()  # Stop accepting new connections

            # Wait for the agent thread to finish
            if self.agent_thread:
                self.agent_thread.join()  # Wait for the thread to finish
                self.agent_thread = None  # Reset thread reference

            # Remove the socket file only after the server socket is closed
            if self.server_sock:  # Check if the server socket exists
                self.server_sock.close()  # Close the server socket
                os.remove(self.sock_path)
