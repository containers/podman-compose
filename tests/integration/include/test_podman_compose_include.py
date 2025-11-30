# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from pathlib import Path

from packaging import version

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(suffix: str = "") -> str:
    return os.path.join(os.path.join(test_path(), "include"), f"docker-compose{suffix}.yaml")


class TestPodmanComposeInclude(unittest.TestCase, RunSubprocessMixin):
    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_podman_compose_include(self) -> None:
        """
        Test that podman-compose can execute podman-compose -f <file> up with include
        :return:
        """
        main_path = Path(__file__).parent.parent.parent.parent

        command_up = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "integration", "include", "docker-compose.yaml")),
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

        command_down = ["podman", "rm", "--force"]

        self.run_subprocess_assert_returncode(command_up)
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        expected_output = b'"localhost/nopush/podman-compose-test:latest"\n' * 2
        self.assertEqual(out, expected_output)
        # Get container ID to remove it
        out, _ = self.run_subprocess_assert_returncode(command_container_id)
        self.assertNotEqual(out, b"")
        container_ids = out.decode().strip().split("\n")
        container_ids = [container_id.replace('"', "") for container_id in container_ids]
        command_down.extend(container_ids)
        out, _ = self.run_subprocess_assert_returncode(command_down)
        # cleanup test image(tags)
        self.assertNotEqual(out, b"")
        # check container did not exist anymore
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        self.assertEqual(out, b"")

    def test_podman_compose_include_dict(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                compose_yaml_path("_include_dict"),
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "ps",
                "-a",
                "--filter",
                "label=io.podman.compose.project=include",
                "--format",
                '"{{.Names}}"',
            ])
            # two services from included compose files were created
            self.assertEqual(out, b'"include_web_1"\n"include_web2_1"\n')
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("_include_dict"),
                "down",
                "-t",
                "0",
            ])
