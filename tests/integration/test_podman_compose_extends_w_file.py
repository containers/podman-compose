# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "extends_w_file"), "docker-compose.yml")


class TestComposeExtendsWithFile(unittest.TestCase, RunSubprocessMixin):
    def test_extends_w_file(self):  # when file is Dockerfile for building the image
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
            self.assertIn("extends_w_file_web_1", str(output))
            self.assertIn("extends_w_file_important_web_1", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
