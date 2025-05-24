# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "nets_test_ip"), "docker-compose.yml")


class TestComposeNetsTestIp(unittest.TestCase, RunSubprocessMixin):
    # test if services retain custom ipv4_address and mac_address matching the subnet provided
    # in networks top-level element
    def test_nets_test_ip(self) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "-d",
                ],
            )

            expected_results = [
                (
                    "web1",
                    b"inet 172.19.1.10/24 ",
                    b"link/ether 02:01:01:00:01:01 ",
                    b"inet 172.19.2.10/24 ",
                    b"link/ether 02:01:01:00:02:01 ",
                    b"",
                ),
                ("web2", b"", b"", b"inet 172.19.2.11/24 ", b"", b"link/ether 02:01:01:00:02:02 "),
                ("web3", b"", b"", b"inet 172.19.2.", b"", b""),
                ("web4", b"inet 172.19.1.13/24 ", b"", b"inet 172.19.2.", b"", b""),
            ]

            for (
                service_name,
                shared_network_ip,
                shared_network_mac_address,
                internal_network_ip,
                internal_network_mac_address,
                mac_address,
            ) in expected_results:
                output, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "exec",
                    service_name,
                    "ip",
                    "a",
                ])
                self.assertIn(shared_network_ip, output)
                self.assertIn(shared_network_mac_address, output)
                self.assertIn(internal_network_ip, output)
                self.assertIn(internal_network_mac_address, output)
                self.assertIn(mac_address, output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
