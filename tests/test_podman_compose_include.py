# SPDX-License-Identifier: GPL-2.0

import unittest
from pathlib import Path

from .test_utils import RunSubprocessMixin


class TestPodmanComposeInclude(unittest.TestCase, RunSubprocessMixin):
    def test_podman_compose_include(self):
        """
        Test that podman-compose can execute podman-compose -f <file> up with include
        :return:
        """
        main_path = Path(__file__).parent.parent

        command_up = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "include", "docker-compose.yaml")),
            "up",
            "-d",
        ]

        command_check_container = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=include",
            "--format",
            '"{{.Image}}"',
        ]

        command_container_id = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=include",
            "--format",
            '"{{.ID}}"',
        ]

        command_down = ["podman", "rm", "--force", "CONTAINER_ID"]

        self.run_subprocess_assert_returncode(command_up)
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        self.assertEqual(out, b'"localhost/nopush/podman-compose-test:latest"\n')
        # Get container ID to remove it
        out, _ = self.run_subprocess_assert_returncode(command_container_id)
        self.assertNotEqual(out, b"")
        container_id = out.decode().strip().replace('"', "")
        command_down[3] = container_id
        out, _ = self.run_subprocess_assert_returncode(command_down)
        # cleanup test image(tags)
        self.assertNotEqual(out, b"")
        # check container did not exists anymore
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        self.assertEqual(out, b"")
