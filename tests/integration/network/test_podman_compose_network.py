# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_networks.py

Tests the podman networking parameters
"""

# pylint: disable=redefined-outer-name
import os
import unittest
from typing import Generator

from packaging import version

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanComposeNetwork(RunSubprocessMixin, unittest.TestCase):
    @staticmethod
    def compose_file() -> str:
        """Returns the path to the compose file used for this test module"""
        return os.path.join(test_path(), "nets_test_ip", "docker-compose.yml")

    def teardown(self) -> Generator[None, None, None]:
        """
        Ensures that the services within the "profile compose file" are removed between
        each test case.
        """
        # run the test case
        yield

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

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_networks(self) -> None:
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

        check_cmd = [
            podman_compose_path(),
            "-f",
            self.compose_file(),
            "ps",
            "--format",
            '"{{.Names}}"',
        ]
        out, _ = self.run_subprocess_assert_returncode(check_cmd)
        self.assertIn(b"nets_test_ip_web1_1", out)
        self.assertIn(b"nets_test_ip_web2_1", out)

        expected_wget = {
            "172.19.1.10": "test1",
            "172.19.2.10": "test1",
            "172.19.2.11": "test2",
            "web3": "test3",
            "172.19.1.13": "test4",
        }

        for service in ("web1", "web2"):
            for ip, expect in expected_wget.items():
                wget_cmd = [
                    podman_compose_path(),
                    "-f",
                    self.compose_file(),
                    "exec",
                    service,
                    "wget",
                    "-q",
                    "-O-",
                    f"http://{ip}:8001/index.txt",
                ]
                out, _ = self.run_subprocess_assert_returncode(wget_cmd)
                self.assertEqual(f"{expect}\r\n", out.decode('utf-8'))

        expected_macip = {
            "web1": {
                "eth0": ["172.19.1.10", "02:01:01:00:01:01"],
                "eth1": ["172.19.2.10", "02:01:01:00:02:01"],
            },
            "web2": {"eth0": ["172.19.2.11", "02:01:01:00:02:02"]},
        }

        for service, interfaces in expected_macip.items():
            ip_cmd = [
                podman_compose_path(),
                "-f",
                self.compose_file(),
                "exec",
                service,
                "ip",
                "addr",
                "show",
            ]
            out, _ = self.run_subprocess_assert_returncode(ip_cmd)
            for interface, values in interfaces.items():
                ip, mac = values
                self.assertIn(f"ether {mac}", out.decode('utf-8'))
                self.assertIn(f"inet {ip}/", out.decode('utf-8'))

    def test_down_with_network(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                os.path.join(test_path(), "network", "docker-compose.yml"),
                "up",
                "-d",
            ])
            output, _, _ = self.run_subprocess(["podman", "network", "ls"])
            self.assertIn("network_mystack", output.decode())
        finally:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                os.path.join(test_path(), "network", "docker-compose.yml"),
                "down",
            ])
            output, _, _ = self.run_subprocess(["podman", "network", "ls"])
            self.assertNotIn("network_mystack", output.decode())
