# SPDX-License-Identifier: GPL-2.0

import os
import textwrap
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "stdin_behavior"), "docker-compose.yaml")


class TestStdinBehavior(unittest.TestCase, RunSubprocessMixin):
    def setUp(self) -> None:
        # Clean up any leftover containers before each test
        self.run_subprocess(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ],
        )

    def tearDown(self) -> None:
        # Clean up any leftover containers after each test
        self.run_subprocess(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ],
        )

    def test_up_does_not_pass_stdin_to_container(self) -> None:
        """
        When stdin is piped to podman-compose up, the container should not
        receive it. A container with stdin_open=true should wait for input
        instead of reading the piped data.
        """
        self.run_subprocess(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "--abort-on-container-exit",
            ],
            input=b"hello\n",
            timeout=5,
        )

        output, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "logs",
                "--no-log-prefix",
                "--no-color",
            ],
            0,
        )
        self.assertEqual(output, b'Waiting...\nReceived:\n')

    def test_run_passes_stdin_to_container(self) -> None:
        """
        When stdin is piped to podman-compose run, the container should
        receive it, matching docker-compose behavior.
        """
        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "test",
            ],
            input=b"hello\n",
        )
        self.assertIn(b"Received: hello", out)

    def test_exec_passes_stdin_to_container(self) -> None:
        """
        When stdin is piped to podman-compose exec, the container should
        receive it, matching docker-compose behavior.
        """
        # Start the container in detached mode first
        self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "-d",
            ],
        )

        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "exec",
                "test",
                "sh",
                "-c",
                "read line; echo 'ReceivedExec:' $line",
            ],
            input=b"exec-hello\n",
        )
        self.assertEqual(out, b'exec-hello\r\nReceivedExec: exec-hello\r\n')

    def test_compose_file_from_stdin(self) -> None:
        """
        Reading a compose file from stdin via ``-f -`` must still work
        even though stdin is not forwarded to containers.
        """
        compose_content = b"""services:
  test:
    image: nopush/podman-compose-test
    command: ["echo", "from-stdin-compose"]
"""
        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                "-",
                "config",
            ],
            input=compose_content,
        )
        expected = textwrap.dedent("""\
            services:
              test:
                command:
                - echo
                - from-stdin-compose
                image: nopush/podman-compose-test

            """)
        self.assertEqual(out.decode("utf-8"), expected)
