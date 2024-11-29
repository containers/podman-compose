# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

import requests

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "nets_test1"), "docker-compose.yml")


class TestComposeNetsTest1(unittest.TestCase, RunSubprocessMixin):
    # test if port mapping works as expected
    def test_nets_test1(self):
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "-d",
                ],
            )
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
            ])
            self.assertIn(b"nets_test1-web1-1", output)
            self.assertIn(b"nets_test1-web2-1", output)

            response = requests.get('http://localhost:8001/index.txt')
            self.assertTrue(response.ok)
            self.assertEqual(response.text, "test1\n")

            response = requests.get('http://localhost:8002/index.txt')
            self.assertTrue(response.ok)
            self.assertEqual(response.text, "test2\n")

            # inspect 1st container
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "nets_test1-web1-1",
            ])
            container_info = json.loads(output.decode('utf-8'))[0]

            # check if network got default name
            self.assertEqual(
                list(container_info["NetworkSettings"]["Networks"].keys())[0], "nets_test1_default"
            )

            # check if Host port is the same as provided by the service port
            self.assertEqual(
                container_info['NetworkSettings']["Ports"],
                {"8001/tcp": [{"HostIp": "", "HostPort": "8001"}]},
            )

            self.assertEqual(container_info["Config"]["Hostname"], "web1")

            # inspect 2nd container
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "nets_test1-web2-1",
            ])
            container_info = json.loads(output.decode('utf-8'))[0]
            self.assertEqual(
                list(container_info["NetworkSettings"]["Networks"].keys())[0], "nets_test1_default"
            )

            self.assertEqual(
                container_info['NetworkSettings']["Ports"],
                {"8001/tcp": [{"HostIp": "", "HostPort": "8002"}]},
            )

            self.assertEqual(container_info["Config"]["Hostname"], "web2")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
