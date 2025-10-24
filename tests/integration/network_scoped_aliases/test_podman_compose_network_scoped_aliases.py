# SPDX-License-Identifier: GPL-2.0

# pylint: disable=redefined-outer-name
import os
import unittest

from packaging import version

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanComposeNetworkScopedAliases(RunSubprocessMixin, unittest.TestCase):
    @staticmethod
    def compose_file() -> str:
        """Returns the path to the compose file used for this test module"""
        return os.path.join(test_path(), "network_scoped_aliases", "docker-compose.yaml")

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_network_scoped_aliases(self) -> None:
        try:
            self.up()
            self.verify()
        finally:
            self.down()

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

    def verify(self) -> None:
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

    def parse_dnslookup(self, output: str) -> list[str]:
        lines = output.splitlines()
        addresses = []
        for line in lines:
            if line.startswith("Address"):
                addr = line.split(":", 1)[1].strip()
                if ":" not in addr:
                    addresses.append(addr)

        return list(sorted(set(addresses)))
