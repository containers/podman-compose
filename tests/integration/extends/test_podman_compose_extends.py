# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "extends"), "docker-compose.yaml")


class TestComposeExteds(unittest.TestCase, RunSubprocessMixin):
    def test_extends_service_launch_echo(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "echo",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "logs",
                "--no-log-prefix",
                "--no-color",
                "echo",
            ])
            self.assertEqual(output, b"Zero\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_extends_service_launch_echo1(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "echo1",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "logs",
                "--no-log-prefix",
                "--no-color",
                "echo1",
            ])
            self.assertEqual(output, b"One\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_extends_service_launch_env1(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "env1",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "logs",
                "--no-log-prefix",
                "--no-color",
                "env1",
            ])
            lines = output.decode('utf-8').split('\n')
            # Test selected env variables to improve robustness
            lines = sorted([
                line
                for line in lines
                if line.startswith("BAR")
                or line.startswith("BAZ")
                or line.startswith("FOO")
                or line.startswith("HOME")
                or line.startswith("PATH")
                or line.startswith("container")
            ])
            self.assertEqual(
                lines,
                [
                    'BAR=local',
                    'BAZ=local',
                    'FOO=original',
                    'HOME=/root',
                    'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                    'container=podman',
                ],
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
