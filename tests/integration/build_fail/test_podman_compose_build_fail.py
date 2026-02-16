# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    """Returns the path to the compose file used for this test module"""
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
                "test",
            ],
            expected_returncode=127,
        )
        self.assertIn("RUN this_command_does_not_exist", str(output))
        self.assertIn("this_command_does_not_exist: not found", str(error))
        self.assertIn("while running runtime: exit status 127", str(error))

    def test_dockerfile_does_not_exist(self):
        out, error = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "build",
                "test_no_dockerfile",
            ],
            expected_returncode=1,
        )
        error = error.decode('utf-8')
        result = '\n'.join(error.splitlines()[-1:])

        expected_path = os.path.join(os.path.dirname(__file__), "context_no_file")
        expected = f'OSError: Dockerfile not found in {expected_path}'

        self.assertEqual(expected, result)

    def test_custom_dockerfile_does_not_exist(self):
        out, error = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "build",
                "test_no_custom_dockerfile",
            ],
            expected_returncode=1,
        )
        error = error.decode('utf-8')
        result = '\n'.join(error.splitlines()[-1:])

        expected_path = os.path.join(os.path.dirname(__file__), "context_no_file/Dockerfile-alt")
        expected = f'OSError: Dockerfile not found in {expected_path}'

        self.assertEqual(expected, result)
