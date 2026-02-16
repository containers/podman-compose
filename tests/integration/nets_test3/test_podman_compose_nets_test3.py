# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from packaging import version
from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "nets_test3"), "docker-compose.yml")


@unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
class TestComposeNetsTest3(unittest.TestCase, RunSubprocessMixin):
    # test if services can access the networks of other services using their respective aliases
    @parameterized.expand([
        ("nets_test3_web2_1", "web3", b"test3", 0),
        ("nets_test3_web2_1", "alias11", b"test3", 0),
        ("nets_test3_web2_1", "alias12", b"test3", 0),
        ("nets_test3_web2_1", "alias21", b"test3", 0),
        ("nets_test3_web1_1", "web3", b"test3", 0),
        ("nets_test3_web1_1", "alias11", b"test3", 0),
        ("nets_test3_web1_1", "alias12", b"test3", 0),
        # connection fails as web1 service does not know net2 and its aliases
        ("nets_test3_web1_1", "alias21", b"", 1),
    ])
    def test_nets_test3(
        self,
        container_name: str,
        network_alias_name: str,
        expected_text: bytes,
        expected_returncode: int,
    ) -> None:
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
            # check connection from different services to network aliases of web3 service
            cmd = [
                "podman",
                "exec",
                "-it",
                f"{container_name}",
                "/bin/busybox",
                "wget",
                "-O",
                "-",
                "-o",
                "/dev/null",
                f"http://{network_alias_name}:8001/index.txt",
            ]
            out, _, returncode = self.run_subprocess(cmd)
            self.assertEqual(expected_returncode, returncode)
            self.assertEqual(expected_text, out.strip())
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
