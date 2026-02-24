# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    """ "Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "build/git_url_context")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposeBuildGitUrlAsContext(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ("git_url_context_test_context_1", "data_1.txt", b'test1\r\n'),
        ("git_url_context_test_context_1", "data_2.txt", b'test2\r\n'),
        ("git_url_context_test_context_inline_1", "data_1.txt", b'test1\r\n'),
        ("git_url_context_test_context_inline_1", "data_2.txt", b'test2\r\n'),
    ])
    def test_build_git_url_as_context(self, container_name, file_name, output):
        # test if container can access specific files from git repository when git url is used as
        # a build context
        try:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "exec",
                "-ti",
                f"{container_name}",
                "sh",
                "-c",
                f"cat {file_name}",
            ])
            self.assertEqual(out, output)
        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
