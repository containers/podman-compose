# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    """Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "exec")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposeExtraHosts(unittest.TestCase, RunSubprocessMixin):
    def test_exec(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "build",
                "--no-cache",
            ])

            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "-d",
            ])

            # TTY auto detected (no tty)
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "exec",
                    "web1",
                    "tty",
                    "-s",
                ],
                expected_returncode=1,  # exit code 1 == no tty
            )

            # TTY auto detected (tty emulated by 'script' command)
            self.run_subprocess_assert_returncode(
                [
                    "script",
                    "--return",
                    "--quiet",
                    "--log-out",
                    "/dev/null",
                    "--command",
                    f"{podman_compose_path()} -f {compose_yaml_path()} exec web1 tty -s",
                ],
                expected_returncode=0,  # exit code 0 == tty
            )

            # TTY disabled (even though an emulated tty is available through the 'script' command)
            self.run_subprocess_assert_returncode(
                [
                    "script",
                    "--return",
                    "--log-out",
                    "/dev/null",
                    "--quiet",
                    "--command",
                    f"{podman_compose_path()} -f {compose_yaml_path()} exec --no-tty web1 tty -s",
                ],
                expected_returncode=1,  # exit code 1 == no tty
            )

            # TTY enabled (tty emulated by 'script' command)
            self.run_subprocess_assert_returncode(
                [
                    "script",
                    "--return",
                    "--log-out",
                    "/dev/null",
                    "--quiet",
                    "--command",
                    f"{podman_compose_path()} -f {compose_yaml_path()} exec --tty web1 tty -s",
                ],
                expected_returncode=0,  # exit code 0 == tty
            )

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
