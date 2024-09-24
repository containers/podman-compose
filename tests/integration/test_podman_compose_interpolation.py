# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "interpolation"), "docker-compose.yml")


class TestComposeInterpolation(unittest.TestCase, RunSubprocessMixin):
    def test_interpolation(self):
        try:
            self.run_subprocess_assert_returncode([
                "env",
                "EXAMPLE_VARIABLE_USER=test_user",
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "logs",
            ])
            self.assertIn("EXAMPLE_VARIABLE='Host user: test_user'", str(output))
            self.assertIn("EXAMPLE_BRACES='Host user: test_user'", str(output))
            self.assertIn("EXAMPLE_COLON_DASH_DEFAULT='My default'", str(output))
            self.assertIn("EXAMPLE_DASH_DEFAULT='My other default'", str(output))
            self.assertIn("EXAMPLE_DOT_ENV='This value is from the .env file'", str(output))
            self.assertIn("EXAMPLE_EMPTY=''", str(output))
            self.assertIn("EXAMPLE_LITERAL='This is a $literal'", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
