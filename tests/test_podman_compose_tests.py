"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""

# pylint: disable=redefined-outer-name
import os
import time
import unittest

from .test_podman_compose import run_subprocess
from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path


class TestPodmanCompose(unittest.TestCase):
    def test_exit_from(self):
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "exit-from", "docker-compose.yaml"),
            "up",
        ]

        out, _, return_code = run_subprocess(up_cmd + ["--exit-code-from", "sh1"])
        self.assertEqual(return_code, 1)

        out, _, return_code = run_subprocess(up_cmd + ["--exit-code-from", "sh2"])
        self.assertEqual(return_code, 2)

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

        out, _, return_code = run_subprocess(run_cmd)
        self.assertIn(b'127.0.0.1\tlocalhost', out)

        # Run it again to make sure we can run it twice. I saw an issue where a second run, with the container left up,
        # would fail
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

        out, _, return_code = run_subprocess(run_cmd)
        assert b'127.0.0.1\tlocalhost' in out
        self.assertEqual(return_code, 0)

        # This leaves a container running. Not sure it's intended, but it matches docker-compose
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "deps", "docker-compose.yaml"),
            "down",
        ]

        out, _, return_code = run_subprocess(run_cmd)
        self.assertEqual(return_code, 0)

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
            out, _, return_code = run_subprocess(up_cmd)
            self.assertEqual(return_code, 0)

        finally:
            out, _, return_code = run_subprocess(down_cmd)
            self.assertEqual(return_code, 0)

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
            out, _, return_code = run_subprocess(["podman", "volume", "create", "my-app-data"])
            self.assertEqual(return_code, 0)
            out, _, return_code = run_subprocess([
                "podman",
                "volume",
                "create",
                "actual-name-of-volume",
            ])
            self.assertEqual(return_code, 0)

            out, _, return_code = run_subprocess(up_cmd)
            self.assertEqual(return_code, 0)

            run_subprocess(["podman", "inspect", "volume", ""])

        finally:
            out, _, return_code = run_subprocess(down_cmd)
            run_subprocess(["podman", "volume", "rm", "my-app-data"])
            run_subprocess(["podman", "volume", "rm", "actual-name-of-volume"])
            self.assertEqual(return_code, 0)

    def test_down_with_orphans(self):
        container_id, _, return_code = run_subprocess([
            "podman",
            "run",
            "--rm",
            "-d",
            "busybox",
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

        out, _, return_code = run_subprocess(down_cmd)
        self.assertEqual(return_code, 0)

        _, _, exists = run_subprocess([
            "podman",
            "container",
            "exists",
            container_id.decode("utf-8"),
        ])

        self.assertEqual(exists, 1)
