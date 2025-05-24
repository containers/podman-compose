# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "exit_from"), "docker-compose.yaml")


class TestComposeExitFrom(unittest.TestCase, RunSubprocessMixin):
    def test_exit_code_sh1(self) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "--exit-code-from=sh1",
                ],
                1,
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_exit_code_sh2(self) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "--exit-code-from=sh2",
                ],
                2,
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_podman_compose_exit_from(self) -> None:
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "up",
        ]

        self.run_subprocess_assert_returncode(up_cmd + ["--exit-code-from", "sh1"], 1)
        self.run_subprocess_assert_returncode(up_cmd + ["--exit-code-from", "sh2"], 2)
