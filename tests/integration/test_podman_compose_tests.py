# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""

# pylint: disable=redefined-outer-name
import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


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
            "--volumes",
        ]

        try:
            self.run_subprocess_assert_returncode(up_cmd)

        finally:
            self.run_subprocess_assert_returncode(down_cmd)

    def test_down_with_vols(self):
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "vol", "docker-compose.yaml"),
            "up",
            "-d",
        ]

        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "vol", "docker-compose.yaml"),
            "down",
            "--volumes",
        ]

        try:
            self.run_subprocess_assert_returncode(["podman", "volume", "create", "my-app-data"])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "create",
                "actual-name-of-volume",
            ])

            self.run_subprocess_assert_returncode(up_cmd)
            self.run_subprocess(["podman", "inspect", "volume", ""])

        finally:
            out, _, return_code = self.run_subprocess(down_cmd)
            self.run_subprocess(["podman", "volume", "rm", "my-app-data"])
            self.run_subprocess(["podman", "volume", "rm", "actual-name-of-volume"])
            self.assertEqual(return_code, 0)

    def test_down_with_orphans(self):
        container_id, _ = self.run_subprocess_assert_returncode([
            "podman",
            "run",
            "--rm",
            "-d",
            "nopush/podman-compose-test",
            "dumb-init",
            "/bin/busybox",
            "httpd",
            "-f",
            "-h",
            "/etc/",
            "-p",
            "8000",
        ])

        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "ports", "docker-compose.yml"),
            "down",
            "--volumes",
            "--remove-orphans",
        ]

        self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            [
                "podman",
                "container",
                "exists",
                container_id.decode("utf-8"),
            ],
            1,
        )

    def test_down_with_network(self):
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
