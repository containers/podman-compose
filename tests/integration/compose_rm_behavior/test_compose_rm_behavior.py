import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(scenario: str) -> str:
    return os.path.join(
        os.path.join(test_path(), "compose_rm_behavior"), f"docker-compose_{scenario}.yaml"
    )


class TestComposeRmBehavior(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ("default", ["rm"], set()),
        (
            "default",
            ["rm", "app"],
            {
                "compose_rm_behavior_db_1",
                "compose_rm_behavior_no_deps_1",
            },
        ),
        (
            "default",
            ["rm", "no_deps"],
            {
                "compose_rm_behavior_app_1",
                "compose_rm_behavior_db_1",
            },
        ),
    ])
    def test_compose_rm(
        self, scenario: str, command_args: list[str], expect_remaining: set[str]
    ) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "up", "-d"],
            )

            # stop containers before rm (rm only removes stopped containers by default)
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "stop"],
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

            self.assertEqual(actual_containers, expect_remaining)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "down",
                "-t",
                "0",
            ])

    def test_compose_rm_stop_flag(self) -> None:
        scenario = "default"
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "up", "-d"],
            )

            # rm --stop should stop and remove running containers
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(scenario),
                    "rm",
                    "-s",
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

            self.assertEqual(actual_containers, set())
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "down",
                "-t",
                "0",
            ])

    def test_compose_rm_force_flag(self) -> None:
        scenario = "default"
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "up", "-d"],
            )

            # rm -f should force remove running containers
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(scenario),
                    "rm",
                    "-f",
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

            self.assertEqual(actual_containers, set())
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "down",
                "-t",
                "0",
            ])

    def test_compose_rm_volumes_flag(self) -> None:
        scenario = "volumes"
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "up", "-d"],
            )

            # stop containers before rm (rm only removes stopped containers by default)
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "stop"],
            )

            # rm -v should remove anonymous volumes attached to containers
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(scenario),
                    "rm",
                    "-v",
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

            self.assertEqual(actual_containers, set())
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "down",
                "-t",
                "0",
            ])
