# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "container_name_run"), "docker-compose.yml")


class TestContainerNameRun(unittest.TestCase, RunSubprocessMixin):
    def setUp(self) -> None:
        # Clean up any leftover containers from previous runs
        self.run_subprocess(
            [
                "podman",
                "rm",
                "-f",
                "my_custom_run_container",
                "cli_override_name",
            ],
        )
        self.run_subprocess(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ],
        )

    def tearDown(self) -> None:
        self.run_subprocess(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ],
        )

    def test_run_uses_container_name(self) -> None:
        self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "test",
            ],
            0,
        )
        out, _ = self.run_subprocess_assert_returncode(
            [
                "podman",
                "ps",
                "-a",
                "--filter",
                "label=io.podman.compose.project=container_name_run",
                "--format",
                "{{.Names}}",
            ],
            0,
        )
        self.assertEqual(b'my_custom_run_container\n', out)

    def test_run_cli_name_overrides_container_name(self) -> None:
        self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "--name",
                "cli_override_name",
                "test",
            ],
            0,
        )
        out, _ = self.run_subprocess_assert_returncode(
            [
                "podman",
                "ps",
                "-a",
                "--filter",
                "label=io.podman.compose.project=container_name_run",
                "--format",
                "{{.Names}}",
            ],
            0,
        )
        self.assertEqual(b'cli_override_name\n', out)
