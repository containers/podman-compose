# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from packaging import version

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version


def base_path() -> str:
    """Returns the base path for the project"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def test_path() -> str:
    """Returns the path to the tests directory"""
    return os.path.join(base_path(), "tests/integration")


def podman_compose_path() -> str:
    """Returns the path to the podman compose script"""
    return os.path.join(base_path(), "podman_compose.py")


class TestPodmanComposePodArgs(unittest.TestCase, RunSubprocessMixin):
    def load_pod_info(self, pod_name: str) -> dict:
        output, _ = self.run_subprocess_assert_returncode([
            "podman",
            "pod",
            "inspect",
            pod_name,
        ])
        pod_info = json.loads(output.decode('utf-8'))
        # Podman 5.0 changed pod inspect to always output a list.
        # Check type to support both old and new version.
        if isinstance(pod_info, list):
            return pod_info[0]
        return pod_info

    def run_pod_args_test(self, config: str, args: list, expected: list) -> None:
        """
        Helper to run podman up with a docker-compose.yml config, additional
        (--pod-args) arguments and compare the CreateCommand of the resulting
        pod with an expected value
        """
        pod_name = "pod_" + config
        command_up = (
            [
                "python3",
                os.path.join(base_path(), "podman_compose.py"),
                "-f",
                os.path.join(
                    base_path(),
                    "tests",
                    "integration",
                    "pod_args",
                    config,
                    "docker-compose.yml",
                ),
            ]
            + args
            + [
                "up",
                "--no-start",
            ]
        )

        try:
            self.run_subprocess_assert_returncode(command_up)

            pod_info = self.load_pod_info(pod_name)
            self.assertEqual(
                pod_info['CreateCommand'],
                ["podman", "pod", "create", "--name=" + pod_name] + expected,
            )

        finally:
            command_rm_pod = ["podman", "pod", "rm", pod_name]
            self.run_subprocess_assert_returncode(command_rm_pod)

    def test_x_podman_pod_args_unset_unset(self) -> None:
        """
        Test that podman-compose will use the default pod-args when unset in
        both docker-compose.yml and command line
        """
        self.run_pod_args_test(
            "custom_pod_args_unset",
            [],
            ["--infra=false", "--share="],
        )

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_x_podman_pod_args_unset_empty(self) -> None:
        """
        Test that podman-compose will use empty pod-args when unset in
        docker-compose.yml and passing an empty value on the command line
        """
        self.run_pod_args_test(
            "custom_pod_args_unset",
            ["--pod-args="],
            [],
        )

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_x_podman_pod_args_unset_set(self) -> None:
        """
        Test that podman-compose will use the passed pod-args when unset in
        docker-compose.yml and passing a non-empty value on the command line
        """
        self.run_pod_args_test(
            "custom_pod_args_unset",
            ["--pod-args=--infra=false --share= --cpus=1"],
            ["--infra=false", "--share=", "--cpus=1"],
        )

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_x_podman_pod_args_empty_unset(self) -> None:
        """
        Test that podman-compose will use empty pod-args when set to an
        empty value in docker-compose.yml and unset on the command line
        """
        self.run_pod_args_test(
            "custom_pod_args_empty",
            [],
            [],
        )

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_x_podman_pod_args_empty_empty(self) -> None:
        """
        Test that podman-compose will use empty pod-args when set to an
        empty value in both docker-compose.yml and command line
        """
        self.run_pod_args_test(
            "custom_pod_args_empty",
            ["--pod-args="],
            [],
        )

    def test_x_podman_pod_args_empty_set(self) -> None:
        """
        Test that podman-compose will use the passed pod-args when set to an
        empty value in docker-compose.yml and passing a non-empty value on the
        command line
        """
        self.run_pod_args_test(
            "custom_pod_args_empty",
            ["--pod-args=--infra=false --share= --cpus=1"],
            ["--infra=false", "--share=", "--cpus=1"],
        )

    def test_x_podman_pod_args_set_unset(self) -> None:
        """
        Test that podman-compose will use the set pod-args when set to a
        non-empty value in docker-compose.yml and unset on the command line
        """
        self.run_pod_args_test(
            "custom_pod_args_set",
            [],
            ["--infra=false", "--share=", "--cpus=2"],
        )

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_x_podman_pod_args_set_empty(self) -> None:
        """
        Test that podman-compose will use empty pod-args when set to a
        non-empty value in docker-compose.yml and passing an empty value on
        the command line
        """
        self.run_pod_args_test(
            "custom_pod_args_set",
            ["--pod-args="],
            [],
        )

    def test_x_podman_pod_args_set_set(self) -> None:
        """
        Test that podman-compose will use the passed pod-args when set to a
        non-empty value in both docker-compose.yml and command line
        """
        self.run_pod_args_test(
            "custom_pod_args_set",
            ["--pod-args=--infra=false --share= --cpus=1"],
            ["--infra=false", "--share=", "--cpus=1"],
        )
