# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""

# pylint: disable=redefined-outer-name
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
            "--volumes",
        ]

        try:
            self.run_subprocess_assert_returncode(up_cmd)

        finally:
            self.run_subprocess_assert_returncode(down_cmd)

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
