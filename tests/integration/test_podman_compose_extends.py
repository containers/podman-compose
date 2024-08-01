# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "extends"), "docker-compose.yaml")


class TestComposeExteds(unittest.TestCase, RunSubprocessMixin):
    def test_extends_service_launch_echo(self):
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

    def test_extends_service_launch_echo1(self):
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

    def test_extends_service_launch_env1(self):
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
                "env1",
            ])
            lines = output.decode('utf-8').split('\n')
            # HOSTNAME name is random string so is ignored in asserting
            lines = sorted([line for line in lines if not line.startswith("HOSTNAME")])
            self.assertEqual(
                lines,
                [
                    '',
                    'BAR=local',
                    'BAZ=local',
                    'FOO=original',
                    'HOME=/root',
                    'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                    'TERM=xterm',
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
