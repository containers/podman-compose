# SPDX-License-Identifier: GPL-2.0

import os
import unittest

import requests

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "nethost"), "docker-compose.yaml")


class TestComposeNethost(unittest.TestCase, RunSubprocessMixin):
    # check if container listens for http requests and sends response back
    # as network_mode: host allows to connect to container easily
    def test_nethost(self):
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(), "up", "-d"],
            )

            container_id, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "ps",
                    "--format",
                    '{{.ID}}',
                ],
            )
            container_id = container_id.decode('utf-8').split('\n')[0]
            output, _ = self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "exec",
                    "-it",
                    container_id,
                    "sh",
                    "-c",
                    "echo test_123 >> /tmp/test.txt",
                ],
            )
            response = requests.get('http://localhost:8123/test.txt')
            self.assertEqual(response.ok, True)
            self.assertEqual(response.text, "test_123\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
