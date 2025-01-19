# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "env-tests"), "container-compose.yml")


class TestComposeEnv(unittest.TestCase, RunSubprocessMixin):
    """Test that inline environment variable overrides environment variable from compose file."""

    def test_env(self):
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "-l",
                "monkey",
                "-e",
                "ZZVAR1=myval2",
                "env-test",
            ])
            self.assertIn("ZZVAR1='myval2'", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
