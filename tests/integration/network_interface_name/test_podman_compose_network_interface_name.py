# SPDX-License-Identifier: GPL-2.0

# pylint: disable=redefined-outer-name
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanComposeNetworkInterfaceName(RunSubprocessMixin, unittest.TestCase):
    def compose_file(self) -> str:
        return os.path.join(test_path(), "network_interface_name", "docker-compose.yml")

    def up(self) -> None:
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            self.compose_file(),
            "up",
            "-d",
            "--force-recreate",
        ]
        self.run_subprocess_assert_returncode(up_cmd)

    def down(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            self.compose_file(),
            "kill",
            "-a",
        ]
        self.run_subprocess(down_cmd)

    def test_interface_name(self) -> None:
        try:
            self.up()

            interfaces_cmd = [
                podman_compose_path(),
                "-f",
                self.compose_file(),
                "exec",
                "web",
                "ls",
                "/sys/class/net",
                "--color=never",
            ]
            out, _ = self.run_subprocess_assert_returncode(interfaces_cmd)
            self.assertEqual("customName0  lo\r\n", out.decode())
        finally:
            self.down()
