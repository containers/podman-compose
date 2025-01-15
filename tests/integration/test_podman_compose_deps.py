# SPDX-License-Identifier: GPL-2.0
import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


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
