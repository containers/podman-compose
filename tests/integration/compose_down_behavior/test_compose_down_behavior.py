# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(scenario: str) -> str:
    return os.path.join(
        os.path.join(test_path(), "compose_down_behavior"), f"docker-compose_{scenario}.yaml"
    )


class TestComposeDownBehavior(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ("default", ["down"], set()),
        (
            "default",
            ["down", "app"],
            {
                "compose_down_behavior_db_1",
                "compose_down_behavior_no_deps_1",
            },
        ),
        (
            "default",
            ["down", "db"],
            {
                "compose_down_behavior_no_deps_1",
            },
        ),
    ])
    def test_compose_down(
        self, scenario: str, command_args: list[str], expect_containers: set[str]
    ) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "up", "-d"],
            )

            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(scenario),
                    *command_args,
                ],
            )

            out, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(scenario),
                    "ps",
                    "--format",
                    '{{ .Names }}',
                ],
            )

            actual_containers = set()
            for line in out.decode('utf-8').strip().split('\n'):
                name = line.strip()
                if name:
                    actual_containers.add(name)

            self.assertEqual(actual_containers, expect_containers)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "down",
                "-t",
                "0",
            ])
