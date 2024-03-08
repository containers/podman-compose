# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""

# pylint: disable=redefined-outer-name
import os
import unittest

from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path
from .test_utils import RunSubprocessMixin


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    def test_exit_from(self):
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "exit-from", "docker-compose.yaml"),
            "up",
        ]

        self.run_subprocess_assert_returncode(up_cmd + ["--exit-code-from", "sh1"], 1)
        self.run_subprocess_assert_returncode(up_cmd + ["--exit-code-from", "sh2"], 2)

    def test_run(self):
        """
        This will test depends_on as well
        """
        run_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "deps", "docker-compose.yaml"),
            "run",
            "--rm",
            "sleep",
            "/bin/sh",
            "-c",
            "wget -q -O - http://web:8000/hosts",
        ]

        out, _ = self.run_subprocess_assert_returncode(run_cmd)
        self.assertIn(b'127.0.0.1\tlocalhost', out)

        # Run it again to make sure we can run it twice. I saw an issue where a second run, with
        # the container left up, would fail
        run_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "deps", "docker-compose.yaml"),
            "run",
            "--rm",
            "sleep",
            "/bin/sh",
            "-c",
            "wget -q -O - http://web:8000/hosts",
        ]

        out, _ = self.run_subprocess_assert_returncode(run_cmd)
        self.assertIn(b'127.0.0.1\tlocalhost', out)

        # This leaves a container running. Not sure it's intended, but it matches docker-compose
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "deps", "docker-compose.yaml"),
            "down",
        ]

        self.run_subprocess_assert_returncode(down_cmd)

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
