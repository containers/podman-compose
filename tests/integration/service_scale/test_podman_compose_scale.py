# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from packaging import version

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(test_ref_folder: str) -> str:
    return os.path.join(test_path(), "service_scale", test_ref_folder, "docker-compose.yml")


@unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
class TestComposeScale(unittest.TestCase, RunSubprocessMixin):
    # scale-up using `scale` parameter in docker-compose.yml
    def test_scaleup_scale_parameter(self) -> None:
        try:
            output, _, return_code = self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path("scaleup_scale_parameter"),
                "up",
                "-d",
            ])
            self.assertEqual(return_code, 0)
            output, _, return_code = self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path("scaleup_scale_parameter"),
                "ps",
                "-q",
            ])
            self.assertEqual(len(output.splitlines()), 2)
        finally:
            self.run_subprocess_assert_returncode([
                "podman",
                "rm",
                "--force",
                "-t",
                "0",
                "podman-compose_service1_1",
                "podman-compose_service1_2",
            ])
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("scaleup_scale_parameter"),
                "down",
                "-t",
                "0",
            ])

    # scale-up using `deploy => replicas` parameter in docker-compose.yml
    def test_scaleup_deploy_replicas_parameter(self) -> None:
        try:
            output, _, return_code = self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_deploy_replicas_parameter'),
                "up",
                "-d",
            ])
            self.assertEqual(return_code, 0)
            output, _, return_code = self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path("scaleup_deploy_replicas_parameter"),
                "ps",
                "-q",
            ])
            self.assertEqual(len(output.splitlines()), 3)
        finally:
            self.run_subprocess_assert_returncode([
                "podman",
                "rm",
                "--force",
                "-t",
                "0",
                "podman-compose_service1_1",
                "podman-compose_service1_2",
                "podman-compose_service1_3",
            ])
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_deploy_replicas_parameter'),
                "down",
                "-t",
                "0",
            ])

    # scale-up using `--scale <SERVICE>=<number of replicas>` argument in CLI
    def test_scaleup_cli(self) -> None:
        try:
            output, _, return_code = self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_cli'),
                "up",
                "-d",
            ])
            self.assertEqual(return_code, 0)
            output, _, return_code = self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_cli'),
                "up",
                "-d",
                "--scale",
                "service1=4",
            ])
            self.assertEqual(return_code, 0)

            output, _, return_code = self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_cli'),
                "ps",
                "-q",
            ])
            self.assertEqual(len(output.splitlines()), 4)
        finally:
            self.run_subprocess_assert_returncode([
                "podman",
                "rm",
                "--force",
                "-t",
                "0",
                "podman-compose_service1_1",
                "podman-compose_service1_2",
                "podman-compose_service1_3",
                "podman-compose_service1_4",
            ])
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_cli'),
                "down",
                "-t",
                "0",
            ])
