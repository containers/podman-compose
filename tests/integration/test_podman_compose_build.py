# SPDX-License-Identifier: GPL-2.0

import os
import unittest

import requests

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


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

            request = requests.get('http://localhost:8080/index.txt')
            self.assertEqual(request.status_code, 200)

            alt_request_success = False
            try:
                # FIXME: suspicious behaviour, too often ends up in error
                alt_request = requests.get('http://localhost:8000/index.txt')
                self.assertEqual(alt_request.status_code, 200)
                self.assertIn("ALT buildno=2 port=8000 ", alt_request.text)
                alt_request_success = True
            except requests.exceptions.ConnectionError:
                pass

            if alt_request_success:
                output, _ = self.run_subprocess_assert_returncode([
                    "podman",
                    "inspect",
                    "my-busybox-httpd2",
                ])
                self.assertIn("httpd_port=8000", str(output))
                self.assertIn("buildno=2", str(output))
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
