# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest
from typing import Any

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(scenario: str) -> str:
    return os.path.join(
        os.path.join(test_path(), "compose_up_behavior"), f"docker-compose_{scenario}.yaml"
    )


class TestComposeDownBehavior(unittest.TestCase, RunSubprocessMixin):
    def get_existing_containers(self, scenario: str) -> dict[str, Any]:
        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "ps",
                "--format",
                'json',
            ],
        )
        containers = json.loads(out)
        return {
            c.get("Names")[0]: {
                "name": c.get("Names")[0],
                "id": c.get("Id"),
                "service_name": c.get("Labels", {}).get("io.podman.compose.service", ""),
                "config_hash": c.get("Labels", {}).get("io.podman.compose.config-hash", ""),
                "exited": c.get("Exited"),
            }
            for c in containers
        }

    @parameterized.expand([
        (
            "service_change_app",
            "service_change_base",
            ["up"],
            {"app"},
        ),
        (
            "service_change_app",
            "service_change_base",
            ["up", "app"],
            {"app"},
        ),
        (
            "service_change_app",
            "service_change_base",
            ["up", "db"],
            set(),
        ),
        (
            "service_change_db",
            "service_change_base",
            ["up"],
            {"db", "app"},
        ),
        (
            "service_change_db",
            "service_change_base",
            ["up", "app"],
            {"db", "app"},
        ),
        (
            "service_change_db",
            "service_change_base",
            ["up", "db"],
            {"db", "app"},
        ),
    ])
    def test_recreate_on_config_changed(
        self,
        change_to: str,
        running_scenario: str,
        command_args: list[str],
        expect_recreated_services: set[str],
    ) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(running_scenario), "up", "-d"],
            )

            original_containers = self.get_existing_containers(running_scenario)

            out, err = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "--verbose",
                    "-f",
                    compose_yaml_path(change_to),
                    *command_args,
                    "-d",
                ],
            )

            new_containers = self.get_existing_containers(change_to)
            recreated_services = {
                c.get("service_name")
                for c in original_containers.values()
                if new_containers.get(c.get("name"), {}).get("id") != c.get("id")
            }

            self.assertEqual(
                recreated_services,
                expect_recreated_services,
                msg=f"Expected services to be recreated: {expect_recreated_services}, "
                f"but got: {recreated_services}, containers: "
                f"[{original_containers}, {new_containers}]",
            )
            self.assertTrue(
                all([c.get("exited") is False for c in new_containers.values()]),
                msg="Not all containers are running after up command",
            )

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(change_to),
                "down",
                "-t",
                "0",
            ])
