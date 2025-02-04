# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "no_services"), "docker-compose.yaml")


class TestComposeNoServices(unittest.TestCase, RunSubprocessMixin):
    # test if a network was created, but not the services
    def test_no_services(self):
        try:
            output, return_code = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "-d",
                ],
            )
            self.assertEqual(
                b'WARNING:__main__:WARNING: unused networks: shared-network\n', return_code
            )

            container_id, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
                "--format",
                '{{.ID}}',
            ])
            self.assertEqual(container_id, b"")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
