# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_targeted_service.py

Tests that the podman-compose `build` and `run` commands activate their
profiles when a specific service (or services) is targeted.
"""

# pylint: disable=redefined-outer-name
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(test_path(), "profile", "docker-compose-only-profiles.yml")


class TestComposeTargetedServices(unittest.TestCase, RunSubprocessMixin):
    def test_build_profile_one_target_service(self) -> None:
        try:
            out, _ = self.run_subprocess_assert_returncode(
                [
                    "coverage",
                    "run",
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "build",
                    "test_2",
                ],
                0,
            )
            self.assertIn(b"FROM nopush/podman-compose-test", out)
            self.run_subprocess_assert_returncode(["podman", "image", "exists", "test_2:latest"], 0)
        finally:
            self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "rmi",
                    "test_2:latest",
                ],
                0,
            )

    def test_build_profile_two_target_services(self) -> None:
        # "build" command can have several target services
        try:
            out, _ = self.run_subprocess_assert_returncode(
                [
                    "coverage",
                    "run",
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "build",
                    "test",
                    "test_2",
                ],
                0,
            )
            self.assertIn(b"FROM nopush/podman-compose-test", out)
            self.run_subprocess_assert_returncode(["podman", "image", "exists", "test:latest"], 0)
            self.run_subprocess_assert_returncode(["podman", "image", "exists", "test_2:latest"], 0)
        finally:
            self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "rmi",
                    "test:latest",
                    "test_2:latest",
                ],
                0,
            )

    def test_run_profile_one_target_service(self) -> None:
        # "run" command can only have one target service
        try:
            out, _ = self.run_subprocess_assert_returncode(
                [
                    "coverage",
                    "run",
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "run",
                    "--rm",
                    "test",
                ],
                0,
            )
            self.assertIn(b'test\r\n', out)
        finally:
            self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "rmi",
                    "test:latest",
                ],
                0,
            )

    def test_targeted_service_is_not_provided_for_profile(self) -> None:
        # without specific service name, profile is not activated
        compose_yaml_path = os.path.join(test_path(), "profile", "docker-compose-only-profiles.yml")
        out, error = self.run_subprocess_assert_returncode(
            [
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                compose_yaml_path,
                "build",
            ],
            0,
        )
        self.assertIn(b"WARNING: No services defined", error)
