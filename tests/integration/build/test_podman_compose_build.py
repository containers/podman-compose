# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    """ "Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "build")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposeBuild(unittest.TestCase, RunSubprocessMixin):
    def test_build(self):
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "build",
                "--no-cache",
            ])

            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "-d",
            ])

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "run",
                "--rm",
                "my-busybox-httpd",
                "cat",
                "/var/www/html/index.txt",
            ])
            self.assertEqual(output.decode().strip(), "web1-test-content")

            # Verify web2 (Dockerfile-alt) image content and build args
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "run",
                "--rm",
                "my-busybox-httpd2",
                "cat",
                "/var/www/html/index.txt",
            ])
            self.assertEqual(output.decode().strip(), "ALT buildno=2 port=8000")

            # Verify build args were baked into the image as env vars
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "run",
                "--rm",
                "my-busybox-httpd2",
                "sh",
                "-c",
                "echo $httpd_port",
            ])
            self.assertEqual(output.decode().strip(), "8000")

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "run",
                "--rm",
                "my-busybox-httpd2",
                "sh",
                "-c",
                "echo $buildno",
            ])
            self.assertEqual(output.decode().strip(), "2")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
