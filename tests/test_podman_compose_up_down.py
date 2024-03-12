# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""

# pylint: disable=redefined-outer-name
import json
import os
import unittest

from parameterized import parameterized

from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path
from .test_utils import RunSubprocessMixin


def profile_compose_file():
    """ "Returns the path to the `profile` compose file used for this test module"""
    return os.path.join(test_path(), "profile", "docker-compose.yml")


class TestUpDown(unittest.TestCase, RunSubprocessMixin):
    def tearDown(self):
        """
        Ensures that the services within the "profile compose file" are removed between each test
        case.
        """
        # run the test case

        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "--profile",
            "profile-1",
            "--profile",
            "profile-2",
            "-f",
            profile_compose_file(),
            "down",
        ]
        self.run_subprocess(down_cmd)

    @parameterized.expand(
        [
            (
                ["--profile", "profile-1", "up", "-d"],
                {"default-service": True, "service-1": True, "service-2": False},
            ),
            (
                ["--profile", "profile-2", "up", "-d"],
                {"default-service": True, "service-1": False, "service-2": True},
            ),
            (
                ["--profile", "profile-1", "--profile", "profile-2", "up", "-d"],
                {"default-service": True, "service-1": True, "service-2": True},
            ),
        ],
    )
    def test_up(self, profiles, expected_services):
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            profile_compose_file(),
        ]
        up_cmd.extend(profiles)

        self.run_subprocess_assert_returncode(up_cmd)

        check_cmd = [
            "podman",
            "container",
            "ps",
            "--format",
            '"{{.Names}}"',
        ]
        out, _ = self.run_subprocess_assert_returncode(check_cmd)

        self.assertEqual(len(expected_services), 3)
        actual_output = out.decode("utf-8")

        actual_services = {}
        for service, _ in expected_services.items():
            actual_services[service] = service in actual_output

        self.assertEqual(expected_services, actual_services)

    def test_healthcheck(self):
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "healthcheck", "docker-compose.yml"),
            "up",
            "-d",
        ]
        self.run_subprocess_assert_returncode(up_cmd)

        command_container_id = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=healthcheck",
            "--format",
            '"{{.ID}}"',
        ]
        out, _ = self.run_subprocess_assert_returncode(command_container_id)
        self.assertNotEqual(out, b"")
        container_id = out.decode("utf-8").strip().replace('"', "")

        command_inspect = ["podman", "container", "inspect", container_id]

        out, _ = self.run_subprocess_assert_returncode(command_inspect)
        out_string = out.decode("utf-8")
        inspect = json.loads(out_string)
        healthcheck_obj = inspect[0]["Config"]["Healthcheck"]
        expected = {
            "Test": ["CMD-SHELL", "/bin/sh -c 'curl -f http://localhost || exit 1'"],
            "StartPeriod": 10000000000,
            "Interval": 60000000000,
            "Timeout": 10000000000,
            "Retries": 3,
        }
        self.assertEqual(healthcheck_obj, expected)

        # StartInterval is not available in the config object
        create_obj = inspect[0]["Config"]["CreateCommand"]
        self.assertIn("--health-startup-interval", create_obj)
