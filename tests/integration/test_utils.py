# SPDX-License-Identifier: GPL-2.0

import os
import re
import subprocess
import time
import unittest
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import Optional

from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from packaging import version
from tzlocal import get_localzone

_podman_version = None


def get_podman_version() -> version.Version:
    """
    Return the *packaging.version.Version* object for the podman binary
    found in PATH (cached after the first call). Raise RuntimeError
    if podman is missing or gives unexpected output.
    """
    global _podman_version
    if _podman_version is None:
        try:
            out = subprocess.check_output(
                ["podman", "--version"], text=True, stderr=subprocess.STDOUT
            )
            # ‘podman version 4.5.0’  →  take last token
            raw = out.strip().split()[-1]
            _podman_version = version.parse(raw)
        except Exception as exc:
            raise RuntimeError("cannot determine podman version") from exc
    return _podman_version


def base_path() -> Path:
    """Returns the base path for the project"""
    return Path(__file__).parent.parent.parent


def test_path() -> str:
    """Returns the path to the tests directory"""
    return os.path.join(base_path(), "tests/integration")


def podman_compose_path() -> str:
    """Returns the path to the podman compose script"""
    return os.path.join(base_path(), "podman_compose.py")


def is_systemd_available() -> bool:
    try:
        with open("/proc/1/comm", encoding="utf-8") as fh:
            return fh.read().strip() == "systemd"
    except FileNotFoundError:
        return False


class RunSubprocessMixin:
    def is_debug_enabled(self) -> bool:
        return "TESTS_DEBUG" in os.environ

    def run_subprocess(
        self,
        args: list[str],
        env: dict[str, str] = {},
        timeout: Optional[float] = None,
        cwd: Optional[Path] = None,
    ) -> tuple[bytes, bytes, int]:
        begin = time.time()
        if self.is_debug_enabled():
            print("TEST_CALL", args)
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ | env,
            cwd=cwd,
        )
        out, err = proc.communicate(timeout=timeout)
        if self.is_debug_enabled():
            print("TEST_CALL completed", time.time() - begin)
            print("STDOUT:", out.decode('utf-8'))
            print("STDERR:", err.decode('utf-8'))
        return out, err, proc.returncode

    def run_subprocess_assert_returncode(
        self,
        args: list[str],
        expected_returncode: int = 0,
        env: dict[str, str] = {},
        timeout: Optional[float] = None,
    ) -> tuple[bytes, bytes]:
        out, err, returncode = self.run_subprocess(args, env=env, timeout=timeout)
        decoded_out = out.decode('utf-8')
        decoded_err = err.decode('utf-8')
        self.assertEqual(  # type: ignore[attr-defined]
            returncode,
            expected_returncode,
            f"Invalid return code of process {returncode} != {expected_returncode}\n"
            f"stdout: {decoded_out}\nstderr: {decoded_err}\n",
        )
        return out, err


class PodmanAwareRunSubprocessMixin(RunSubprocessMixin):
    def retrieve_podman_version(self) -> tuple[int, int, int]:
        out, _ = self.run_subprocess_assert_returncode(["podman", "--version"])
        matcher = re.match(r"\D*(\d+)\.(\d+)\.(\d+)", out.decode('utf-8'))
        if matcher:
            major = int(matcher.group(1))
            minor = int(matcher.group(2))
            patch = int(matcher.group(3))
            return (major, minor, patch)
        raise RuntimeError("Unable to retrieve podman version")


# WORKAROUND for https://github.com/containers/podman/issues/28192
# the healthchecks of Podman rely on systemd timers
# in the test environment (GH actions -> container -> Podman) no systemd is available
# therefore, this class ensures that a periodical healthcheck is run by calling
#   podman healthcheck run <container_name>
# with the help of APScheduler
#
# if systemd is available, this class does nothing
class EnsureHealthcheckRun:
    def __init__(
        self, runner: RunSubprocessMixin, test_case: unittest.TestCase, container_name: str
    ) -> None:
        self.__runner: RunSubprocessMixin = runner

        self.__scheduler: Optional[BackgroundScheduler] = None
        self.__healthcheck_job: Optional[Job] = None
        self.__container_name: str = container_name

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
                # run health checking only for the provided container
                kwargs={"args": ["podman", "healthcheck", "run", f"{self.__container_name}"]},
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
