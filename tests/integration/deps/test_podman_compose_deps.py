# SPDX-License-Identifier: GPL-2.0
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(suffix=""):
    return os.path.join(os.path.join(test_path(), "deps"), f"docker-compose{suffix}.yaml")


class TestComposeBaseDeps(unittest.TestCase, RunSubprocessMixin):
    def test_deps(self):
        try:
            output, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "--rm",
                "sleep",
                "/bin/sh",
                "-c",
                "wget -O - http://web:8000/hosts",
            ])
            self.assertIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertIn(b"deps_web_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_run_nodeps(self):
        try:
            output, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "--rm",
                "--no-deps",
                "sleep",
                "/bin/sh",
                "-c",
                "wget -O - http://web:8000/hosts || echo Failed to connect",
            ])
            self.assertNotIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertNotIn(b"deps_web_1", output)
            self.assertIn(b"Failed to connect", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_up_nodeps(self):
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "--no-deps",
                "--detach",
                "sleep",
            ])
            output, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
            ])
            self.assertNotIn(b"deps_web_1", output)
            self.assertIn(b"deps_sleep_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_podman_compose_run(self):
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
        self.assertIn(b"127.0.0.1\tlocalhost", out)

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
        self.assertIn(b"127.0.0.1\tlocalhost", out)

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


class TestComposeConditionalDeps(unittest.TestCase, RunSubprocessMixin):
    def test_deps_succeeds(self):
        suffix = "-conditional-succeeds"
        try:
            output, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "run",
                "--rm",
                "sleep",
                "/bin/sh",
                "-c",
                "wget -O - http://web:8000/hosts",
            ])
            self.assertIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertIn(b"deps_web_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "down",
            ])

    def test_deps_fails(self):
        suffix = "-conditional-fails"
        try:
            output, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "ps",
            ])
            self.assertNotIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertNotIn(b"deps_web_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "down",
            ])
