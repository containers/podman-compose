# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from pathlib import Path

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "compose_cp_behavior"), "docker-compose.yaml")


class TestComposeCpBehavior(unittest.TestCase, RunSubprocessMixin):
    def test_copy_command(self) -> None:
        host_file = Path("host_file.txt")
        host_file.parent.mkdir(parents=True, exist_ok=True)
        host_file.write_text("This is a test file inside the host.")

        output, _ = self.run_subprocess_assert_returncode(["cat", "host_file.txt"])
        self.assertEqual(b"This is a test file inside the host.", output)

        container_file = "/tmp/copied_from_host.txt"

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "-d",
            ])
            host_file = Path("./container_file.txt")
            assert not host_file.exists(), f"{host_file} must not exist before cp."

            # copy file container_file.txt from container to host
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "cp",
                "my-service:/tmp/container_file.txt",
                ".",
            ])

            assert host_file.exists(), f"{host_file} must exist after cp."

            output, _ = self.run_subprocess_assert_returncode(["cat", "container_file.txt"])
            self.assertEqual(b"This is a test file inside the container.\n", output)

            # copy file host_file.txt from host to container
            # first, check if file does not exist in the container yet
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "exec",
                "my-service",
                "bash",
                "-c",
                f"test ! -f {container_file}",
            ])
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "cp",
                "host_file.txt",
                f"my-service:{container_file}",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "exec",
                "my-service",
                "cat",
                container_file,
            ])
            self.assertEqual(b"This is a test file inside the host.", output)

            # assert that the command fails gracefully when the source path
            # doesn't exist in the container
            _, error = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "cp",
                    "my-service:/tmp/nonexistent.txt",
                    ".",
                ],
                expected_returncode=125,
            )
            self.assertIn(
                b'"/tmp/nonexistent.txt" could not be found on container '
                b'compose_cp_behavior_my-service_1',
                error,
            )

            # assert that the command fails gracefully when copy arguments
            # format is invalid
            _, error = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "cp",
                    "my-service:/tmp/container_file.txt",
                    "my-service:/tmp/host_file.txt",
                ],
                1,
            )
            expected = (
                b'Invalid copy arguments format: source = my-service:/tmp/container_file.txt,'
                b' destination = my-service:/tmp/host_file.txt.'
            )
            self.assertIn(expected, error)

            _, error = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "cp",
                    "host_file.txt",
                    "my-service!container_file.txt",
                ],
                1,
            )
            expected = (
                b'Invalid copy arguments format: source = host_file.txt, '
                b'destination = my-service!container_file.txt.\n'
            )
            self.assertIn(expected, error)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
            host_file.unlink(missing_ok=True)
