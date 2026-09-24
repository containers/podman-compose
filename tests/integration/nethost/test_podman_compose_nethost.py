# SPDX-License-Identifier: GPL-2.0

import os
import socket
import tempfile
import unittest

import requests

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def compose_yaml_content(port: int) -> str:
    return f"""
services:
  web:
    image: busybox
    command: httpd -f -p {port} -h /tmp/
    network_mode: host
"""


class TestComposeNethost(unittest.TestCase, RunSubprocessMixin):
    # check if container listens for http requests and sends response back
    def test_nethost(self) -> None:
        port = get_free_port()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp_compose:
            tmp_compose.write(compose_yaml_content(port))
            tmp_compose_path = tmp_compose.name

        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", tmp_compose_path, "up", "-d"],
            )

            container_id_out, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    tmp_compose_path,
                    "ps",
                    "--format",
                    '{{.ID}}',
                ],
            )
            container_id = container_id_out.decode('utf-8').split('\n')[0]

            output, _ = self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "inspect",
                    "--format",
                    "{{.HostConfig.NetworkMode}}",
                    container_id,
                ],
            )
            self.assertEqual(output.decode().strip(), "host")

            self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "exec",
                    "-it",
                    container_id,
                    "sh",
                    "-c",
                    "echo test_123 >> /tmp/test.txt",
                ],
            )

            response = requests.get(f'http://localhost:{port}/test.txt')
            self.assertEqual(response.ok, True)
            self.assertEqual(response.text, "test_123\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                tmp_compose_path,
                "down",
                "-t",
                "0",
            ])
            os.unlink(tmp_compose_path)
