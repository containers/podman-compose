# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin


def base_path():
    """Returns the base path for the project"""
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def test_path():
    """Returns the path to the tests directory"""
    return os.path.join(base_path(), "tests/integration")


def podman_compose_path():
    """Returns the path to the podman compose script"""
    return os.path.join(base_path(), "podman_compose.py")


# If a compose file has userns_mode set, setting in_pod to True, results in error.
# Default in_pod setting is True, unless compose file provides otherwise.
# Compose file provides custom in_pod option, which can be overridden by command line in_pod option.
# Test all combinations of command line argument in_pod and compose file argument in_pod.
class TestPodmanComposeInPod(unittest.TestCase, RunSubprocessMixin):
    # compose file provides x-podman in_pod=false
    def test_x_podman_in_pod_false_command_line_in_pod_not_exists(self):
        """
        Test that podman-compose will not create a pod, when x-podman in_pod=false and command line
        does not provide this option
        """
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_false",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        down_cmd = [
            "python3",
            podman_compose_path(),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_false",
                "docker-compose.yml",
            ),
            "down",
        ]

        try:
            self.run_subprocess_assert_returncode(command_up)

        finally:
            self.run_subprocess_assert_returncode(down_cmd)
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_false"]
            # throws an error, can not actually find this pod because it was not created
            self.run_subprocess_assert_returncode(command_rm_pod, expected_returncode=1)

    def test_x_podman_in_pod_false_command_line_in_pod_true(self):
        """
        Test that podman-compose does not allow pod creating even with command line in_pod=True
        when --userns and --pod are set together: throws an error
        """
        # FIXME: creates a pod anyway, although it should not
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=True",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_false",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        try:
            out, err = self.run_subprocess_assert_returncode(command_up)
            self.assertEqual(b"Error: --userns and --pod cannot be set together" in err, True)

        finally:
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_false"]
            # should throw an error of not being able to find this pod (because it should not have
            # been created) and have expected_returncode=1 (see FIXME above)
            self.run_subprocess_assert_returncode(command_rm_pod)

    def test_x_podman_in_pod_false_command_line_in_pod_false(self):
        """
        Test that podman-compose will not create a pod as command line sets in_pod=False
        """
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=False",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_false",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        down_cmd = [
            "python3",
            podman_compose_path(),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_false",
                "docker-compose.yml",
            ),
            "down",
        ]

        try:
            self.run_subprocess_assert_returncode(command_up)

        finally:
            self.run_subprocess_assert_returncode(down_cmd)
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_false"]
            # can not actually find this pod because it was not created
            self.run_subprocess_assert_returncode(command_rm_pod, 1)

    def test_x_podman_in_pod_false_command_line_in_pod_empty_string(self):
        """
        Test that podman-compose will not create a pod, when x-podman in_pod=false and command line
        command line in_pod=""
        """
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_false",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        down_cmd = [
            "python3",
            podman_compose_path(),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_false",
                "docker-compose.yml",
            ),
            "down",
        ]

        try:
            self.run_subprocess_assert_returncode(command_up)

        finally:
            self.run_subprocess_assert_returncode(down_cmd)
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_false"]
            # can not actually find this pod because it was not created
            self.run_subprocess_assert_returncode(command_rm_pod, 1)

    # compose file provides x-podman in_pod=true
    def test_x_podman_in_pod_true_command_line_in_pod_not_exists(self):
        """
        Test that podman-compose does not allow pod creating when --userns and --pod are set
        together even when x-podman in_pod=true: throws an error
        """
        # FIXME: creates a pod anyway, although it should not
        # Container is not created, so command 'down' is not needed
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_true",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        try:
            out, err = self.run_subprocess_assert_returncode(command_up)
            self.assertEqual(b"Error: --userns and --pod cannot be set together" in err, True)

        finally:
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_true"]
            # should throw an error of not being able to find this pod (it should not have been
            # created) and have expected_returncode=1 (see FIXME above)
            self.run_subprocess_assert_returncode(command_rm_pod)

    def test_x_podman_in_pod_true_command_line_in_pod_true(self):
        """
        Test that podman-compose does not allow pod creating when --userns and --pod are set
        together even when x-podman in_pod=true and and command line in_pod=True: throws an error
        """
        # FIXME: creates a pod anyway, although it should not
        # Container is not created, so command 'down' is not needed
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=True",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_true",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        try:
            out, err = self.run_subprocess_assert_returncode(command_up)
            self.assertEqual(b"Error: --userns and --pod cannot be set together" in err, True)

        finally:
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_true"]
            # should throw an error of not being able to find this pod (because it should not have
            # been created) and have expected_returncode=1 (see FIXME above)
            self.run_subprocess_assert_returncode(command_rm_pod)

    def test_x_podman_in_pod_true_command_line_in_pod_false(self):
        """
        Test that podman-compose will not create a pod as command line sets in_pod=False
        """
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=False",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_true",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        down_cmd = [
            "python3",
            podman_compose_path(),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_true",
                "docker-compose.yml",
            ),
            "down",
        ]

        try:
            self.run_subprocess_assert_returncode(command_up)

        finally:
            self.run_subprocess_assert_returncode(down_cmd)
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_false"]
            # can not actually find this pod because it was not created
            self.run_subprocess_assert_returncode(command_rm_pod, 1)

    def test_x_podman_in_pod_true_command_line_in_pod_empty_string(self):
        """
        Test that podman-compose does not allow pod creating when --userns and --pod are set
        together even when x-podman in_pod=true and command line in_pod="": throws an error
        """
        # FIXME: creates a pod anyway, although it should not
        # Container is not created, so command 'down' is not needed
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_true",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        try:
            out, err = self.run_subprocess_assert_returncode(command_up)
            self.assertEqual(b"Error: --userns and --pod cannot be set together" in err, True)

        finally:
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_true"]
            # should throw an error of not being able to find this pod (because it should not have
            # been created) and have expected_returncode=1 (see FIXME above)
            self.run_subprocess_assert_returncode(command_rm_pod)

    # compose file does not provide x-podman in_pod
    def test_x_podman_in_pod_not_exists_command_line_in_pod_not_exists(self):
        """
        Test that podman-compose does not allow pod creating when --userns and --pod are set
        together: throws an error
        """
        # FIXME: creates a pod anyway, although it should not
        # Container is not created, so command 'down' is not needed
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_not_exists",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        try:
            out, err = self.run_subprocess_assert_returncode(command_up)
            self.assertEqual(b"Error: --userns and --pod cannot be set together" in err, True)

        finally:
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_not_exists"]
            # should throw an error of not being able to find this pod (it should not have been
            # created) and have expected_returncode=1 (see FIXME above)
            self.run_subprocess_assert_returncode(command_rm_pod)

    def test_x_podman_in_pod_not_exists_command_line_in_pod_true(self):
        """
        Test that podman-compose does not allow pod creating when --userns and --pod are set
        together even when x-podman in_pod=true: throws an error
        """
        # FIXME: creates a pod anyway, although it should not
        # Container was not created, so command 'down' is not needed
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=True",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_not_exists",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        try:
            out, err = self.run_subprocess_assert_returncode(command_up)
            self.assertEqual(b"Error: --userns and --pod cannot be set together" in err, True)

        finally:
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_not_exists"]
            # should throw an error of not being able to find this pod (because it should not have
            # been created) and have expected_returncode=1 (see FIXME above)
            self.run_subprocess_assert_returncode(command_rm_pod)

    def test_x_podman_in_pod_not_exists_command_line_in_pod_false(self):
        """
        Test that podman-compose will not create a pod as command line sets in_pod=False
        """
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=False",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_not_exists",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        down_cmd = [
            "python3",
            podman_compose_path(),
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_not_exists",
                "docker-compose.yml",
            ),
            "down",
        ]

        try:
            self.run_subprocess_assert_returncode(command_up)

        finally:
            self.run_subprocess_assert_returncode(down_cmd)

            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_not_exists"]
            # can not actually find this pod because it was not created
            self.run_subprocess_assert_returncode(command_rm_pod, 1)

    def test_x_podman_in_pod_not_exists_command_line_in_pod_empty_string(self):
        """
        Test that podman-compose does not allow pod creating when --userns and --pod are set
        together: throws an error
        """
        # FIXME: creates a pod anyway, although it should not
        # Container was not created, so command 'down' is not needed
        command_up = [
            "python3",
            os.path.join(base_path(), "podman_compose.py"),
            "--in-pod=",
            "-f",
            os.path.join(
                base_path(),
                "tests",
                "integration",
                "in_pod",
                "custom_x-podman_not_exists",
                "docker-compose.yml",
            ),
            "up",
            "-d",
        ]

        try:
            out, err = self.run_subprocess_assert_returncode(command_up)
            self.assertEqual(b"Error: --userns and --pod cannot be set together" in err, True)

        finally:
            command_rm_pod = ["podman", "pod", "rm", "pod_custom_x-podman_not_exists"]
            # should throw an error of not being able to find this pod (because it should not have
            # been created) and have expected_returncode=1 (see FIXME above)
            self.run_subprocess_assert_returncode(command_rm_pod)
