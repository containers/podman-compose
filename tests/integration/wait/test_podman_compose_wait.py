# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest
from datetime import datetime
from datetime import timedelta
from io import BytesIO
from typing import Any
from typing import Final
from typing import Optional

from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from packaging import version
from tzlocal import get_localzone

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import is_systemd_available
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path

EXECUTION_TIMEOUT: Final[float] = 30


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


@unittest.skipIf(
    get_podman_version() < version.parse("4.6.0"), "Wait feature not supported below 4.6.0."
)
class TestComposeWait(unittest.TestCase, RunSubprocessMixin):
    # WORKAROUND for https://github.com/containers/podman/issues/28192
    scheduler: Optional[BackgroundScheduler] = None

    @classmethod
    def setUpClass(cls) -> None:
        # use APScheduler to trigger a healtcheck periodically if systemd and its timers are not
        # available
        if not is_systemd_available():
            cls.scheduler = BackgroundScheduler()
            cls.scheduler.start()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.scheduler is not None:
            cls.scheduler.shutdown(wait=True)

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

        # start the healthcheck job
        self.healthcheck_job: Optional[Job] = None
        if self.scheduler is not None:
            self.healthcheck_job = self.scheduler.add_job(
                func=self.run_subprocess,
                # run health checking only for the wait_app_health_1 container
                kwargs={"args": ["podman", "healthcheck", "run", "wait_app_health_1"]},
                # trigger the healthcheck every 3 seconds (like defined in docker-compose.yml)
                trigger=IntervalTrigger(
                    # trigger the healthcheck every 3 seconds (like defined in docker-compose.yml)
                    seconds=3,
                    # run first healthcheck after 3 seconds (initial interval)
                    start_date=datetime.now(get_localzone()) + timedelta(seconds=3),
                    # stop after 21 seconds = 3s (interval) * 6 (retries) + 3s (initial interval)
                    end_date=datetime.now(get_localzone()) + timedelta(seconds=21),
                ),
            )

    def tearDown(self) -> None:
        # stop and remove the healtcheck job
        if self.scheduler is not None:
            try:
                if self.healthcheck_job is not None:
                    self.scheduler.remove_job(self.healthcheck_job.id)
                else:
                    self.scheduler.remove_all_jobs()
            except JobLookupError:
                # failover
                self.scheduler.remove_all_jobs()

        # clean up compose after every test
        self.run_subprocess([
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "down",
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

    def test_without_wait(self) -> None:
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

    def test_wait(self) -> None:
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

    def test_wait_with_timeout(self) -> None:
        # the execution time of this command must be between 5 and 10 seconds
        with ExecutionTime(
            min_execution_time=timedelta(seconds=5), max_execution_time=timedelta(seconds=10)
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

    def test_wait_with_start(self) -> None:
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
