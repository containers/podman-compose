# SPDX-License-Identifier: GPL-2.0
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "macos_docker_socket"), "docker-compose.yaml")


class TestMacosDockerSocket(unittest.TestCase, RunSubprocessMixin):
    def test_macos_docker_socket(self) -> None:
        if os.uname().sysname != "Darwin":
            self.skipTest("Test only runs on macOS")
        if not os.path.exists("/var/run/docker.sock"):
            self.skipTest("Docker compatibility is not turned on")

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "--build",
                "test-docker-in-docker",
            ])
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
