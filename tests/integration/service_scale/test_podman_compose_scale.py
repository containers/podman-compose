# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(test_ref_folder):
    return os.path.join(test_path(), "service_scale", test_ref_folder, "docker-compose.yml")


class TestComposeScale(unittest.TestCase, RunSubprocessMixin):
    # scale-up using `scale` prarmeter in docker-compose.yml
    def test_scaleup_scale_parameter(self):
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
                podman_compose_path(),
                "-f",
                compose_yaml_path("scaleup_scale_parameter"),
                "down",
                "-t",
                "0",
            ])

    # scale-up using `deploy => replicas` prarmeter in docker-compose.yml
    def test_scaleup_deploy_replicas_parameter(self):
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
                compose_yaml_path("scaleup_scale_parameter"),
                "ps",
                "-q",
            ])
            self.assertEqual(len(output.splitlines()), 2)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_deploy_replicas_parameter'),
                "down",
                "-t",
                "0",
            ])

    # scale-up using `--scale <SERVICE>=<number of replicas>` argument in CLI
    def test_scaleup_cli(self):
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
                "service1=2",
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
                podman_compose_path(),
                "-f",
                compose_yaml_path('scaleup_cli'),
                "down",
                "-t",
                "0",
            ])
