# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(file: str) -> str:
    return os.path.join(os.path.join(test_path(), "interpolation"), file)


class TestComposeInterpolation(unittest.TestCase, RunSubprocessMixin):
    def test_interpolation(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                "env",
                "EXAMPLE_VARIABLE_USER=test_user",
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose.yml"),
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose.yml"),
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
                compose_yaml_path("docker-compose.yml"),
                "down",
            ])

    def test_nested_interpolation(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                "env",
                "DEFAULT=nested",
                "TEST_LABELS=foo",
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose-nested.yml"),
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose-nested.yml"),
                "logs",
            ])
            self.assertIn(
                "EXAMPLE_COLON_DASH_DEFAULT_WITH_INTERPOLATION='My default is nested'", str(output)
            )
            self.assertIn(
                "EXAMPLE_DASH_DEFAULT_WITH_INTERPOLATION='My default is nested'", str(output)
            )
            self.assertIn("EXAMPLE_DOTENV_INTERPOLATION='Dotenv with default nested'", str(output))

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "interpolation_labels_test_1",
            ])
            inspect_output = json.loads(output)
            labels_dict = inspect_output[0].get("Config", {}).get("Labels", {})
            self.assertIn(('empty_foo', 'test_labels'), labels_dict.items())
            self.assertIn(('notset_foo', 'test_labels'), labels_dict.items())
            self.assertIn(('test.empty_foo', 'empty_foo'), labels_dict.items())
            self.assertIn(('test.notset_foo', 'notset_foo'), labels_dict.items())
            self.assertIn(('empty_foo.test2', 'test2(`empty_foo`)'), labels_dict.items())
            self.assertIn(('notset_foo.test2', 'test2(`notset_foo`)'), labels_dict.items())

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose-nested.yml"),
                "down",
            ])
