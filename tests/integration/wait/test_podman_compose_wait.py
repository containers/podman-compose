# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest
from datetime import timedelta
from io import BytesIO
from typing import Final

from packaging import version

from tests.integration.test_utils import EnsureHealthcheckRun
from tests.integration.test_utils import ExecutionTime
from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path

EXECUTION_TIMEOUT: Final[float] = 30


def compose_yaml_path() -> str:
    return os.path.join(test_path(), "wait", "docker-compose.yml")


def compose_yaml_fail_path() -> str:
    return os.path.join(test_path(), "wait", "docker-compose-fail.yml")


@unittest.skipIf(
    get_podman_version() < version.parse("4.6.0"), "Wait feature not supported below 4.6.0."
)
class TestComposeWait(unittest.TestCase, RunSubprocessMixin):
    def setUp(self) -> None:
        # build the test image before starting the tests
        # this is not possible in setUpClass method, because the run_subprocess_* methods are not
        # available as classmethods
        self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "build",
        ])

    def _get_health_status(self, container_name: str) -> str:
        output, _ = self.run_subprocess_assert_returncode([
            "podman",
            "inspect",
            container_name,
        ])
        inspect = json.load(BytesIO(output))

        self.assertEqual(len(inspect), 1)
        self.assertIn("State", inspect[0])
        self.assertIn("Health", inspect[0]["State"])
        self.assertIn("Status", inspect[0]["State"]["Health"])

        return inspect[0]["State"]["Health"]["Status"]

    def _is_running(self, container_name: str) -> bool:
        output, _ = self.run_subprocess_assert_returncode([
            "podman",
            "inspect",
            container_name,
        ])
        inspect = json.load(BytesIO(output))

        self.assertEqual(len(inspect), 1)
        self.assertIn("State", inspect[0])
        self.assertIn("Running", inspect[0]["State"])
        return inspect[0]["State"]["Running"]

    def _compose_down(self) -> None:
        self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "down",
            "-t",
            "0",
        ])

    def test_without_wait(self) -> None:
        try:
            with EnsureHealthcheckRun(
                runner=self, test_case=self, container_name="wait_app_health_1"
            ):
                # the execution time of this command must be not more then 10 seconds
                # otherwise this test case makes no sense
                with ExecutionTime(max_execution_time=timedelta(seconds=10)):
                    self.run_subprocess_assert_returncode([
                        podman_compose_path(),
                        "-f",
                        compose_yaml_path(),
                        "up",
                        "-d",
                    ])

                output, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "ps",
                ])
                self.assertIn(b"wait_app_health_1", output)
                self.assertIn(b"wait_app_1", output)

                self.assertTrue(self._is_running("wait_app_1"))

                health = self._get_health_status("wait_app_health_1")
                self.assertEqual(health, "starting")
        finally:
            self._compose_down()

    def test_wait(self) -> None:
        try:
            with EnsureHealthcheckRun(
                runner=self, test_case=self, container_name="wait_app_health_1"
            ):
                # the execution time of this command must be at least 10 seconds,
                # because of the sleep command in entrypoint.sh
                with ExecutionTime(min_execution_time=timedelta(seconds=10)):
                    self.run_subprocess_assert_returncode(
                        [
                            podman_compose_path(),
                            "-f",
                            compose_yaml_path(),
                            "up",
                            "-d",
                            "--wait",
                        ],
                        timeout=EXECUTION_TIMEOUT,
                    )

                output, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "ps",
                ])
                self.assertIn(b"wait_app_health_1", output)
                self.assertIn(b"wait_app_1", output)

                self.assertTrue(self._is_running("wait_app_1"))

                health = self._get_health_status("wait_app_health_1")
                self.assertEqual(health, "healthy")
        finally:
            self._compose_down()

    def test_wait_with_timeout(self) -> None:
        try:
            with EnsureHealthcheckRun(
                runner=self, test_case=self, container_name="wait_app_health_1"
            ):
                # the execution time of this command must be between 5 and 10 seconds
                with ExecutionTime(
                    min_execution_time=timedelta(seconds=5),
                    max_execution_time=timedelta(seconds=10),
                ):
                    self.run_subprocess_assert_returncode(
                        [
                            podman_compose_path(),
                            "-f",
                            compose_yaml_path(),
                            "up",
                            "-d",
                            "--wait",
                            "--wait-timeout",
                            "5",
                        ],
                        timeout=EXECUTION_TIMEOUT,
                    )

                output, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "ps",
                ])
                self.assertIn(b"wait_app_health_1", output)
                self.assertIn(b"wait_app_1", output)

                self.assertTrue(self._is_running("wait_app_1"))

                health = self._get_health_status("wait_app_health_1")
                self.assertEqual(health, "starting")
        finally:
            self._compose_down()

    def test_wait_with_start(self) -> None:
        try:
            with EnsureHealthcheckRun(
                runner=self, test_case=self, container_name="wait_app_health_1"
            ):
                # the execution time of this command must be not more then 10 seconds
                # otherwise this test case makes no sense
                with ExecutionTime(max_execution_time=timedelta(seconds=10)):
                    # podman-compose create does not exist
                    # therefore bring the containers up and kill them immediately again
                    self.run_subprocess_assert_returncode([
                        podman_compose_path(),
                        "-f",
                        compose_yaml_path(),
                        "up",
                        "-d",
                    ])
                    self.run_subprocess_assert_returncode([
                        podman_compose_path(),
                        "-f",
                        compose_yaml_path(),
                        "kill",
                        "--all",
                    ])

                output, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "ps",
                ])
                self.assertIn(b"wait_app_health_1", output)
                self.assertIn(b"wait_app_1", output)

                self.assertFalse(self._is_running("wait_app_health_1"))
                self.assertFalse(self._is_running("wait_app_1"))

                # the execution time of this command must be at least 10 seconds,
                # because of the sleep command in entrypoint.sh
                with ExecutionTime(min_execution_time=timedelta(seconds=10)):
                    self.run_subprocess_assert_returncode(
                        [
                            podman_compose_path(),
                            "-f",
                            compose_yaml_path(),
                            "start",
                            "--wait",
                        ],
                        timeout=EXECUTION_TIMEOUT,
                    )

                self.assertTrue(self._is_running("wait_app_1"))

                health = self._get_health_status("wait_app_health_1")
                self.assertEqual(health, "healthy")
        finally:
            self._compose_down()

    def test_wait_with_failing_service(self) -> None:
        # a service that fails (exits with a non-zero code) must cause `up --wait` to
        # return a non-zero exit code, matching docker-compose behaviour
        try:
            _, _, returncode = self.run_subprocess(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_fail_path(),
                    "up",
                    "-d",
                    "--wait",
                ],
                timeout=EXECUTION_TIMEOUT,
            )
            self.assertNotEqual(returncode, 0)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_fail_path(),
                "down",
                "-t",
                "0",
            ])
