# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "env-tests"), "container-compose.yml")


class TestComposeEnv(unittest.TestCase, RunSubprocessMixin):
    """Test that inline environment variable overrides environment variable from compose file."""

    def test_env(self):
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "-l",
                "monkey",
                "-e",
                "ZZVAR1=myval2",
                "env-test",
            ])
            self.assertIn("ZZVAR1='myval2'", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    """
    Tests interpolation of COMPOSE_PROJECT_NAME in the podman-compose config,
    which is different from external environment variables because COMPOSE_PROJECT_NAME
    is a predefined environment variable generated from the `name` value in the top-level
    of the compose.yaml.

    See also
    - https://docs.docker.com/reference/compose-file/interpolation/
    - https://docs.docker.com/reference/compose-file/version-and-name/#name-top-level-element
    - https://docs.docker.com/compose/how-tos/environment-variables/envvars/
    - https://github.com/compose-spec/compose-spec/blob/main/04-version-and-name.md
    """

    def test_project_name(self):
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "project-name-test",
            ])
            self.assertIn("my-project-name", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_project_name_override(self):
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "-e",
                "COMPOSE_PROJECT_NAME=project-name-override",
                "project-name-test",
            ])
            self.assertIn("project-name-override", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
