# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "ipam_default"), "docker-compose.yaml")


class TestComposeIpamDefault(unittest.TestCase, RunSubprocessMixin):
    def test_ipam_default(self) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(), "up", "-d"],
            )

            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "logs",
            ])
            # when container is created, its command echoes 'ipamtest'
            # BUG: figure out why echo is called twice
            self.assertIn("ipamtest", str(output))

            output, _ = self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "inspect",
                    "ipam_default_testipam_1",
                ],
            )
            network_info = json.loads(output.decode('utf-8'))[0]
            network_name = next(iter(network_info["NetworkSettings"]["Networks"].keys()))

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "network",
                "inspect",
                f"{network_name}",
            ])
            network_info = json.loads(output.decode('utf-8'))[0]
            # bridge is the default network driver
            self.assertEqual(network_info['driver'], "bridge")
            self.assertEqual(network_info['ipam_options'], {'driver': 'host-local'})
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
