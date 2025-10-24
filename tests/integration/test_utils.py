# SPDX-License-Identifier: GPL-2.0

import os
import re
import subprocess
import time
from pathlib import Path

from packaging import version

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

    def run_subprocess(self, args: list[str], env: dict[str, str] = {}) -> tuple[bytes, bytes, int]:
        begin = time.time()
        if self.is_debug_enabled():
            print("TEST_CALL", args)
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ | env,
        )
        out, err = proc.communicate()
        if self.is_debug_enabled():
            print("TEST_CALL completed", time.time() - begin)
            print("STDOUT:", out.decode('utf-8'))
            print("STDERR:", err.decode('utf-8'))
        return out, err, proc.returncode

    def run_subprocess_assert_returncode(
        self, args: list[str], expected_returncode: int = 0, env: dict[str, str] = {}
    ) -> tuple[bytes, bytes]:
        out, err, returncode = self.run_subprocess(args, env=env)
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
