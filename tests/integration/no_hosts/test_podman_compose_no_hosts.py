# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "no_hosts"), "compose.yaml")


class TestComposeNoHosts(unittest.TestCase, RunSubprocessMixin):
    def tearDown(self) -> None:
        self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "down",
        ])

    def test_no_hosts_flag(self) -> None:
        """--no-hosts CLI flag should omit podman-managed entries"""
        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "--no-hosts",
            ],
        )
        self.assertNotIn("host.containers.internal", out.decode("utf-8"))

    def test_without_no_hosts_flag(self) -> None:
        """without --no-hosts, container should have podman-managed entries"""
        out, _ = self.run_subprocess_assert_returncode(
            [podman_compose_path(), "-f", compose_yaml_path(), "up"],
        )

        self.assertIn("host.containers.internal", out.decode("utf-8"))
