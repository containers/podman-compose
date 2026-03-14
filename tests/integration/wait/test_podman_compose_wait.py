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


# WORKAROUND for https://github.com/containers/podman/issues/28192
# the healthchecks of Podman rely on systemd timers
# in the test environment (GH actions -> container -> Podman) no systemd is available
# therefore, this class ensures that a periodical healthcheck is run by calling
#   podman healthcheck run <container_name>
# with the help of APScheduler
#
# if systemd is available, this class does nothing
class EnsureHealthcheckRun:
    def __init__(self, runner: RunSubprocessMixin, test_case: unittest.TestCase) -> None:
        self.__runner: RunSubprocessMixin = runner

        self.__scheduler: Optional[BackgroundScheduler] = None
        self.__healthcheck_job: Optional[Job] = None

        # check if systemd is not available
        if not is_systemd_available():
            # initialize APScheduler
            self.__scheduler = BackgroundScheduler()
            self.__scheduler.start()

            # add a clean up to the test case (in case the test fails)
            test_case.addCleanup(self._cleanup_scheduler)

    def _cleanup_scheduler(self) -> None:
        # stop and remove the healtcheck job
        if self.__scheduler is not None:
            try:
                if self.__healthcheck_job is not None:
                    self.__scheduler.remove_job(self.__healthcheck_job.id)
                else:
                    self.__scheduler.remove_all_jobs()
            except JobLookupError:
                # failover
                self.__scheduler.remove_all_jobs()

            # shutdown the scheduler
            self.__scheduler.shutdown(wait=True)

            # prevent this method from being executed twice:
            # after exiting the context manager and during clean up of the test case
            self.__scheduler = None

    def __enter__(self) -> None:
        # start the healthcheck job
        if self.__scheduler is not None:
            self.__healthcheck_job = self.__scheduler.add_job(
                func=self.__runner.run_subprocess,
                # run health checking only for the wait_app_health_1 container
                kwargs={"args": ["podman", "healthcheck", "run", "wait_app_health_1"]},
                trigger=IntervalTrigger(
                    # trigger the healthcheck every 3 seconds (like defined in docker-compose.yml)
                    seconds=3,
                    # run first healthcheck after 3 seconds (initial interval)
                    start_date=datetime.now(get_localzone()) + timedelta(seconds=3),
                    # stop after 21 seconds = 3s (interval) * 6 (retries) + 3s (initial interval)
                    end_date=datetime.now(get_localzone()) + timedelta(seconds=21),
                ),
            )

    def __exit__(self, *_: Any) -> None:
        # clean up after exiting the context manager
        self._cleanup_scheduler()


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
        ])

    def test_without_wait(self) -> None:
        try:
            with EnsureHealthcheckRun(runner=self, test_case=self):
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
            with EnsureHealthcheckRun(runner=self, test_case=self):
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
            with EnsureHealthcheckRun(runner=self, test_case=self):
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
            with EnsureHealthcheckRun(runner=self, test_case=self):
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
