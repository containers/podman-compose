# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest
from io import BytesIO

from tests.integration.test_utils import RunSubprocessMixin, podman_compose_path, test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "merge", "reset_and_override_tags", "reset_tag_attribute_w_extends"), "docker-compose.yml")


class TestComposeResetTagAttributeWithExtends(unittest.TestCase, RunSubprocessMixin):
    def test_reset_w_extends(self) -> None:  # when file is Dockerfile for building the image
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                ],
            )
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
            ])
            self.assertIn("reset_tag_attribute_w_extends_web_1", str(output))

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "reset_tag_attribute_w_extends_web_1"
            ])
            inspect = json.load(BytesIO(output))

            self.assertEqual(len(inspect), 1)
            self.assertIn("NetworkSettings", inspect[0])
            self.assertIn("Ports", inspect[0]["NetworkSettings"])
            self.assertEqual(len(inspect[0]["NetworkSettings"]["Ports"]), 0)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
