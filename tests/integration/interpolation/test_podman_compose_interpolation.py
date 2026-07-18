# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "interpolation"), "docker-compose.yml")


def compose_command_yaml_path() -> str:
    return os.path.join(
        os.path.join(test_path(), "interpolation"), "docker-compose-command-interpolation.yml"
    )


class TestComposeInterpolation(unittest.TestCase, RunSubprocessMixin):
    def test_interpolation(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                "env",
                "EXAMPLE_VARIABLE_USER=test_user",
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "logs",
            ])
            self.assertIn("EXAMPLE_VARIABLE='Host user: test_user'", str(output))
            self.assertIn("EXAMPLE_BRACES='Host user: test_user'", str(output))
            self.assertIn("EXAMPLE_COLON_DASH_DEFAULT='My default'", str(output))
            self.assertIn("EXAMPLE_DASH_DEFAULT='My other default'", str(output))
            self.assertIn("EXAMPLE_DOT_ENV='This value is from the .env file'", str(output))
            self.assertIn("EXAMPLE_EMPTY=''", str(output))
            self.assertIn("EXAMPLE_LITERAL='This is a $literal'", str(output))

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "interpolation_labels_test_1",
            ])
            inspect_output = json.loads(output)
            labels_dict = inspect_output[0].get("Config", {}).get("Labels", {})
            self.assertIn(('TEST', 'test_labels'), labels_dict.items())
            self.assertIn(('TEST.test2', 'test2(`TEST`)'), labels_dict.items())
            self.assertIn(('test.TEST', 'TEST'), labels_dict.items())

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_required_nonempty_variable_missing(self) -> None:
        compose_yaml_path = os.path.join(
            os.path.join(test_path(), "interpolation"), "docker-compose-colon-question-error.yml"
        )
        out, err = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path,
                "up",
            ],
            1,
        )
        self.assertIn(b"required variable NOT_A_VARIABLE is missing a value: Missing variable", err)

    def test_required_set_variable_missing(self) -> None:
        compose_yaml_path = os.path.join(
            os.path.join(test_path(), "interpolation"), "docker-compose-question-error.yml"
        )
        out, err = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path,
                "up",
            ],
            1,
        )
        self.assertIn(b"required variable NOT_A_VARIABLE is missing a value: Missing variable", err)

    def test_command_interpolation_unquoted(self) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_command_yaml_path(),
                    "up",
                ],
                0,
                {"CMD_VAR": "hello_world"},
            )
            output, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_command_yaml_path(),
                    "logs",
                ],
                0,
                {"CMD_VAR": "hello_world"},
            )
            self.assertIn(b"hello_world", output)
        finally:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_command_yaml_path(),
                    "down",
                ],
                0,
                {"CMD_VAR": "hello_world"},
            )

    def test_command_interpolation_unquoted_missing_variable(self) -> None:
        out, err = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_command_yaml_path(),
                "up",
            ],
            1,
        )
        self.assertIn(
            b"required variable CMD_VAR is missing a value: CMD_VAR variable missing", err
        )
