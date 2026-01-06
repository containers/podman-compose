# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def networks_no_services_compose() -> str:
    return compose_yaml_path("docker-compose-networks-no-services.yaml")


def empty_services_compose() -> str:
    return compose_yaml_path("docker-compose-empty-services.yaml")


def compose_yaml_path(filename: str) -> str:
    return os.path.join(os.path.join(test_path(), "no_services"), filename)


class TestComposeNoServices(unittest.TestCase, RunSubprocessMixin):
    # test if a network was created, but not the services
    def test_no_services(self) -> None:
        try:
            _, err = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    networks_no_services_compose(),
                    "up",
                    "-d",
                ],
            )
            self.assertIn(b'WARNING:__main__:WARNING: unused networks: shared-network\n', err)

            container_id, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                networks_no_services_compose(),
                "ps",
                "--format",
                '{{.ID}}',
            ])
            self.assertEqual(container_id, b"")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                networks_no_services_compose(),
                "down",
                "-t",
                "0",
            ])

    def test_empty_services_no_stacktrace(self) -> None:
        try:
            _, err = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                empty_services_compose(),
                "up",
                "-d",
            ])
            self.assertNotIn(b"\nTraceback (most recent call last):\n", err)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                empty_services_compose(),
                "down",
                "-t",
                "0",
            ])
