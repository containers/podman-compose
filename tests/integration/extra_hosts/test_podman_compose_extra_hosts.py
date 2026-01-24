# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    """Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "extra_hosts")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposeExtraHosts(unittest.TestCase, RunSubprocessMixin):
    def test_extra_hosts(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "build",
                "--no-cache",
            ])

            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "-d",
            ])

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
