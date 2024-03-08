# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from pathlib import Path

from .test_utils import RunSubprocessMixin


def base_path():
    """Returns the base path for the project"""
    return Path(__file__).parent.parent


def test_path():
    """Returns the path to the tests directory"""
    return os.path.join(base_path(), "tests")


def podman_compose_path():
    """Returns the path to the podman compose script"""
    return os.path.join(base_path(), "podman_compose.py")


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    def test_extends_w_file_subdir(self):
        """
        Test that podman-compose can execute podman-compose -f <file> up with extended File which
        includes a build context
        :return:
        """
        main_path = Path(__file__).parent.parent

        command_up = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "extends_w_file_subdir", "docker-compose.yml")),
            "up",
            "-d",
        ]

        command_check_container = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "extends_w_file_subdir", "docker-compose.yml")),
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
            str(main_path.joinpath("tests", "extends_w_file_subdir", "docker-compose.yml")),
            "down",
        ])

        self.run_subprocess_assert_returncode([
            "podman",
            "rmi",
            "--force",
            "localhost/subdir_test:me",
        ])

        # check container did not exists anymore
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        self.assertEqual(out, b'')

    def test_extends_w_empty_service(self):
        """
        Test that podman-compose can execute podman-compose -f <file> up with extended File which
        includes an empty service. (e.g. if the file is used as placeholder for more complex
        configurations.)
        """
        main_path = Path(__file__).parent.parent

        command_up = [
            "python3",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "extends_w_empty_service", "docker-compose.yml")),
            "up",
            "-d",
        ]

        self.run_subprocess_assert_returncode(command_up)
