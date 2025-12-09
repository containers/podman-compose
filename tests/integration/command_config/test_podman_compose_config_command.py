# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    """ "Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "commands_fail_exit_code")
    return os.path.join(base_path, "docker-compose.yml")


class TestConfigCommand(unittest.TestCase, RunSubprocessMixin):
    def test_config_quiet(self) -> None:
        """
        Tests podman-compose config command with the --quiet flag.
        """
        config_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "config",
            "--quiet",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)
        self.assertEqual(out.decode("utf-8"), "")
