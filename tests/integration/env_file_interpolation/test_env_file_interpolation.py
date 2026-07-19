# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_base_path() -> str:
    return os.path.join(test_path(), "env_file_interpolation")


class TestEnvFileInterpolation(unittest.TestCase, RunSubprocessMixin):
    def test_env_file_interpolates_from_project_dotenv(self) -> None:
        base_path = compose_base_path()
        path_compose_file = os.path.join(base_path, "docker-compose.yml")
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "logs",
                "--no-log-prefix",
                "--no-color",
            ])
            self.assertEqual(output, b"FOO=bar\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])
