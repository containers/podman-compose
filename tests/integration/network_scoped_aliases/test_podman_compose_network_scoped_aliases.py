# SPDX-License-Identifier: GPL-2.0

# pylint: disable=redefined-outer-name
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanComposeNetworkScopedAliases(RunSubprocessMixin, unittest.TestCase):
    @staticmethod
    def compose_file():
        """Returns the path to the compose file used for this test module"""
        return os.path.join(test_path(), "network_scoped_aliases", "docker-compose.yaml")

    def test_network_scoped_aliases(self):
        try:
            self.up()
            self.verify()
        finally:
            self.down()

    def up(self):
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

    def down(self):
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

    def verify(self):
        expected_results = [
            ("utils-net0", "web1", ["172.19.3.11"]),
            ("utils-net0", "secure-web", ["172.19.3.11"]),
            ("utils-net0", "insecure-web", []),
            ("utils-net1", "web1", ["172.19.4.11"]),
            ("utils-net1", "secure-web", []),
            ("utils-net1", "insecure-web", ["172.19.4.11"]),
        ]

        for utils, service, expected_result in expected_results:
            cmd = [
                podman_compose_path(),
                "-f",
                self.compose_file(),
                "exec",
                utils,
                "nslookup",
                service,
            ]
            out, _, _ = self.run_subprocess(cmd)
            addresses = self.parse_dnslookup(out.decode())
            self.assertEqual(addresses, expected_result)

    def parse_dnslookup(self, output):
        lines = output.splitlines()
        addresses = []
        for line in lines:
            if line.startswith("Address"):
                addr = line.split(":", 1)[1].strip()
                if ":" not in addr:
                    addresses.append(addr)

        return list(sorted(set(addresses)))
