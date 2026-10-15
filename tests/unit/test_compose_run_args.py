# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from podman_compose import PodmanComposeError
from podman_compose import podman_compose


def env_file_tests_dir() -> str:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(repo_root, "tests", "integration", "env_file_tests")


class TestComposeRunArgs(unittest.TestCase):
    def setUp(self) -> None:
        # relative --env-from-file paths are resolved against the working directory
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(env_file_tests_dir())

    def test_env_from_file_can_be_repeated_and_is_made_absolute(self) -> None:
        args = podman_compose._parse_args([  # pylint: disable=protected-access
            "run",
            "--env-from-file",
            "env-files/project-1.env",
            "--env-from-file=env-files/project-2.env",
            "app",
        ])

        self.assertEqual(
            args.env_from_file,
            [
                os.path.join(os.getcwd(), "env-files", "project-1.env"),
                os.path.join(os.getcwd(), "env-files", "project-2.env"),
            ],
        )

    def test_env_from_file_missing(self) -> None:
        with self.assertRaises(PodmanComposeError) as error:
            podman_compose._parse_args([  # pylint: disable=protected-access
                "run",
                "--env-from-file",
                "env-files/project-1.env",
                "--env-from-file",
                "env-files/missing.env",
                "app",
            ])

        missing_path = os.path.join(os.getcwd(), "env-files", "missing.env")
        self.assertEqual(str(error.exception), f"Couldn't find env file: {missing_path}")
