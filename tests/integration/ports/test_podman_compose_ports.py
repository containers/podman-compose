# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_ports.py

Tests the podman compose port command used to show the host port.
"""

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    def test_up_with_ports(self):
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "ports", "docker-compose.yml"),
            "up",
            "-d",
            "--force-recreate",
        ]

        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "ports", "docker-compose.yml"),
            "down",
        ]

        port_cmd = [
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "ports", "docker-compose.yml"),
            "port",
        ]

        udp_arg = ["--protocol", "udp"]

        tcp_arg = ["--protocol", "tcp"]

        try:
            self.run_subprocess_assert_returncode(up_cmd)

            port = self.run_subprocess_assert_returncode(port_cmd + ["web1", "8000"])
            self.assertEqual(port[0].decode().strip(), "8000")

            port = self.run_subprocess_assert_returncode(port_cmd + ["web1", "8001"])
            self.assertNotEqual(port[0].decode().strip(), "8001")

            port = self.run_subprocess_assert_returncode(port_cmd + ["web2", "8002"])
            self.assertEqual(port[0].decode().strip(), "8002")

            port = self.run_subprocess_assert_returncode(port_cmd + udp_arg + ["web2", "8003"])
            self.assertEqual(port[0].decode().strip(), "8003")

            port = self.run_subprocess_assert_returncode(port_cmd + ["web2", "8004"])
            self.assertEqual(port[0].decode().strip(), "8004")

            port = self.run_subprocess_assert_returncode(port_cmd + tcp_arg + ["web2", "8005"])
            self.assertEqual(port[0].decode().strip(), "8005")

            port = self.run_subprocess_assert_returncode(port_cmd + udp_arg + ["web2", "8006"])
            self.assertNotEqual(port[0].decode().strip(), "8006")

            port = self.run_subprocess_assert_returncode(port_cmd + ["web2", "8007"])
            self.assertNotEqual(port[0].decode().strip(), "8007")

        finally:
            self.run_subprocess_assert_returncode(down_cmd)
