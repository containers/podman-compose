# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path():
    """ "Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "build_fail")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposeBuildFail(unittest.TestCase, RunSubprocessMixin):
    def test_build_fail(self):
        output, error = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "build",
            ],
            expected_returncode=127,
        )
        self.assertIn("RUN this_command_does_not_exist", str(output))
        self.assertIn("this_command_does_not_exist: not found", str(error))
        self.assertIn("while running runtime: exit status 127", str(error))
