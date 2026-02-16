# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from pathlib import Path

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "extends_w_file_subdir"), "docker-compose.yml")


class TestComposeExtendsWithFileSubdir(unittest.TestCase, RunSubprocessMixin):
    def test_extends_w_file_subdir(self) -> None:  # when file is Dockerfile for building the image
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
            self.assertIn("extends_w_file_subdir_web_1", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_podman_compose_extends_w_file_subdir(self) -> None:
        """
        Test that podman-compose can execute podman-compose -f <file> up with extended File which
        includes a build context
        :return:
        """
        main_path = Path(__file__).parent.parent.parent.parent

        command_up = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(
                main_path.joinpath(
                    "tests", "integration", "extends_w_file_subdir", "docker-compose.yml"
                )
            ),
            "up",
            "-d",
        ]

        command_check_container = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(
                main_path.joinpath(
                    "tests", "integration", "extends_w_file_subdir", "docker-compose.yml"
                )
            ),
            "ps",
            "--format",
            '{{.Image}}',
        ]

        self.run_subprocess_assert_returncode(command_up)
        # check container was created and exists
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        self.assertEqual(out, b'localhost/subdir_test:me\n')
        # cleanup test image(tags)
        self.run_subprocess_assert_returncode([
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(
                main_path.joinpath(
                    "tests", "integration", "extends_w_file_subdir", "docker-compose.yml"
                )
            ),
            "down",
        ])

        self.run_subprocess_assert_returncode([
            "podman",
            "rmi",
            "--force",
            "localhost/subdir_test:me",
        ])

        # check container did not exist anymore
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        self.assertEqual(out, b'')
