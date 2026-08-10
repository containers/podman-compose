# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    """ "Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "commands_fail_exit_code")
    return os.path.join(base_path, "docker-compose.yml")


def compose_yaml_path_scenario(scenario: str) -> str:
    return os.path.join(test_path(), "command_config", f"docker-compose_{scenario}.yaml")


class TestConfigCommand(unittest.TestCase, RunSubprocessMixin):
    def test_config_quiet(self) -> None:
        """
        Tests podman-compose config command with the --quiet flag.
        """
        config_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "config",
            "--quiet",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)
        self.assertEqual(out.decode("utf-8"), "")

    def test_config_shows_networks_and_default_network(self) -> None:
        config_cmd = [
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "config",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)
        output = out.decode("utf-8")

        self.assertIn("networks:", output)
        self.assertIn("default:", output)

    def test_config_with_named_network(self) -> None:
        config_cmd = [
            podman_compose_path(),
            "-f",
            compose_yaml_path_scenario("one_net"),
            "config",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)
        output = out.decode("utf-8")

        self.assertIn("networks:", output)
        self.assertIn("net0:", output)
        self.assertIn("command_config_net0", output)
        self.assertNotIn("default:", output)

    def test_config_with_external_network(self) -> None:
        config_cmd = [
            podman_compose_path(),
            "-f",
            compose_yaml_path_scenario("external_net"),
            "config",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)
        output = out.decode("utf-8")

        self.assertIn("networks:", output)
        self.assertIn("extnet:", output)
        self.assertIn("external: true", output)
        self.assertNotIn("command_config_extnet", output)

    def test_config_with_network_mode(self) -> None:
        config_cmd = [
            podman_compose_path(),
            "-f",
            compose_yaml_path_scenario("network_mode"),
            "config",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)
        output = out.decode("utf-8")

        self.assertIn("network_mode: host", output)
        # The service itself must not have a networks key injected
        service_section = output.split("services:")[1]
        self.assertNotIn("networks:", service_section)
        self.assertNotIn("default:", service_section)
