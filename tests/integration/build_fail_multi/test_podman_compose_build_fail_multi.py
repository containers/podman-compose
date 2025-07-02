# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    """ "Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "build_fail_multi")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposeBuildFailMulti(unittest.TestCase, RunSubprocessMixin):
    def test_build_fail_multi(self):
        output, error = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "build",
                # prevent the successful build from being cached to ensure it runs long enough
                "--no-cache",
            ],
            expected_returncode=1,
        )
        self.assertIn("RUN false", str(output))
        self.assertIn("while running runtime: exit status 1", str(error))

    def test_push_command_fail(self) -> None:
        # test that push command is able to return other than "0" return code
        # "push" command fails due to several steps missing before running it (logging, tagging)
        try:
            output, error = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "push",
                    "good",
                ],
                expected_returncode=125,
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_run_command_fail(self) -> None:
        # test that run command is able to return other than "0" return code
        try:
            output, error = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "run",
                    "bad",
                ],
                expected_returncode=125,
            )
            self.assertIn("RUN false", str(output))
            self.assertIn("while running runtime: exit status 1", str(error))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
