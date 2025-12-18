# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest
from datetime import datetime
from datetime import timedelta
from io import BytesIO
from typing import Any
from typing import Optional

from podman_compose import strverscmp_lt
from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(test_path(), "wait", "docker-compose.yml")


class ExecutionTime:
    def __init__(
        self,
        min_execution_time: Optional[timedelta] = None,
        max_execution_time: Optional[timedelta] = None,
    ) -> None:
        self.__min_execution_time = min_execution_time
        self.__max_execution_time = max_execution_time

        self.__start_time: Optional[datetime] = None

    def __enter__(self) -> None:
        self.__start_time = datetime.now()

    def __exit__(self, *_: Any) -> None:
        # should normally not happen
        if self.__start_time is None:
            return

        execution_time = datetime.now() - self.__start_time

        if self.__min_execution_time:
            assert execution_time >= self.__min_execution_time
        if self.__max_execution_time:
            assert execution_time <= self.__max_execution_time


@unittest.skipIf(strverscmp_lt(get_podman_version(), "4.6.0"), "feature not supported")
class TestComposeWait(unittest.TestCase, RunSubprocessMixin):
    def __get_health_status(self, container_name: str) -> str:
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

    def __is_running(self, container_name: str) -> bool:
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

    def test_without_wait(self) -> None:
        try:
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

            self.assertTrue(self.__is_running("wait_app_1"))

            health = self.__get_health_status("wait_app_health_1")
            self.assertEqual(health, "starting")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_wait(self) -> None:
        try:
            # the execution time of this command must be at least 10 seconds,
            # because of the sleep command in entrypoint.sh
            with ExecutionTime(min_execution_time=timedelta(seconds=10)):
                self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "-d",
                    "--wait",
                ])

            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
            ])
            self.assertIn(b"wait_app_health_1", output)
            self.assertIn(b"wait_app_1", output)

            self.assertTrue(self.__is_running("wait_app_1"))

            health = self.__get_health_status("wait_app_health_1")
            self.assertEqual(health, "healthy")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_wait_with_timeout(self) -> None:
        try:
            # the execution time of this command must be between 5 and 10 seconds
            with ExecutionTime(
                min_execution_time=timedelta(seconds=5), max_execution_time=timedelta(seconds=10)
            ):
                self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "-d",
                    "--wait",
                    "--wait-timeout",
                    "5",
                ])

            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
            ])
            self.assertIn(b"wait_app_health_1", output)
            self.assertIn(b"wait_app_1", output)

            self.assertTrue(self.__is_running("wait_app_1"))

            health = self.__get_health_status("wait_app_health_1")
            self.assertEqual(health, "starting")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_wait_with_start(self) -> None:
        try:
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

            self.assertFalse(self.__is_running("wait_app_health_1"))
            self.assertFalse(self.__is_running("wait_app_1"))

            # the execution time of this command must be at least 10 seconds,
            # because of the sleep command in entrypoint.sh
            with ExecutionTime(min_execution_time=timedelta(seconds=10)):
                self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "start",
                    "--wait",
                ])

            self.assertTrue(self.__is_running("wait_app_1"))

            health = self.__get_health_status("wait_app_health_1")
            self.assertEqual(health, "healthy")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
