# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from pathlib import Path

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "extends_w_empty_service"), "docker-compose.yml")


class TestComposeExtendsWithEmptyService(unittest.TestCase, RunSubprocessMixin):
    def test_extends_w_empty_service(self):
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
            self.assertIn("extends_w_empty_service_web_1", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_podman_compose_extends_w_empty_service(self):
        """
        Test that podman-compose can execute podman-compose -f <file> up with extended File which
        includes an empty service. (e.g. if the file is used as placeholder for more complex
        configurations.)
        """
        main_path = Path(__file__).parent.parent.parent.parent

        command_up = [
            "python3",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(
                main_path.joinpath(
                    "tests", "integration", "extends_w_empty_service", "docker-compose.yml"
                )
            ),
            "up",
            "-d",
        ]

        self.run_subprocess_assert_returncode(command_up)
