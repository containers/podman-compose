# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_config.py

Tests the podman-compose config command which is used to return defined compose services.
"""

# pylint: disable=redefined-outer-name
import os
import unittest

from parameterized import parameterized

from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path
from .test_utils import RunSubprocessMixin


def profile_compose_file():
    """ "Returns the path to the `profile` compose file used for this test module"""
    return os.path.join(test_path(), "profile", "docker-compose.yml")


class TestComposeConfig(unittest.TestCase, RunSubprocessMixin):
    def test_config_no_profiles(self):
        """
        Tests podman-compose config command without profile enablement.
        """
        config_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            profile_compose_file(),
            "config",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)

        string_output = out.decode("utf-8")
        self.assertIn("default-service", string_output)
        self.assertNotIn("service-1", string_output)
        self.assertNotIn("service-2", string_output)

    @parameterized.expand(
        [
            (
                ["--profile", "profile-1", "config"],
                {"default-service": True, "service-1": True, "service-2": False},
            ),
            (
                ["--profile", "profile-2", "config"],
                {"default-service": True, "service-1": False, "service-2": True},
            ),
            (
                ["--profile", "profile-1", "--profile", "profile-2", "config"],
                {"default-service": True, "service-1": True, "service-2": True},
            ),
        ],
    )
    def test_config_profiles(self, profiles, expected_services):
        """
        Tests podman-compose
        :param profiles: The enabled profiles for the parameterized test.
        :param expected_services: Dictionary used to model the expected "enabled" services in the
            profile. Key = service name, Value = True if the service is enabled, otherwise False.
        """
        config_cmd = ["coverage", "run", podman_compose_path(), "-f", profile_compose_file()]
        config_cmd.extend(profiles)

        out, _ = self.run_subprocess_assert_returncode(config_cmd)

        actual_output = out.decode("utf-8")

        self.assertEqual(len(expected_services), 3)

        actual_services = {}
        for service, _ in expected_services.items():
            actual_services[service] = service in actual_output

        self.assertEqual(expected_services, actual_services)
