# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "podman_compose.py"


def _env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "COMPOSE_PROFILES",
        "COMPOSE_FILE",
        "COMPOSE_PROJECT_NAME",
        "COMPOSE_PROJECT_DIR",
        "COMPOSE_PATH_SEPARATOR",
    ):
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


def _run(
    compose: str, args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "compose.yml"
        path.write_text(compose, encoding="utf-8")
        return subprocess.run(
            ["python3", str(SCRIPT), "--dry-run", "-f", str(path), "-p", "profiles-test", *args],
            cwd=tmp,
            env=_env(env),
            capture_output=True,
            text=True,
            check=False,
        )


COMPOSE = """\
services:
  zeta:
    image: busybox:1.36
    profiles: [zoo, alpha]
  mid:
    image: busybox:1.36
    profiles: [alpha, mid]
  plain:
    image: busybox:1.36
  again:
    image: busybox:1.36
    profiles: [zoo]
"""


class TestComposeConfigProfiles(unittest.TestCase):
    def test_lists_unique_profiles_in_sorted_order(self) -> None:
        result = _run(COMPOSE, ["config", "--profiles"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "alpha\nmid\nzoo\n")
        self.assertEqual(result.stderr, "")

    def test_service_without_profiles_adds_nothing(self) -> None:
        result = _run(
            "services:\n  web:\n    image: busybox:1.36\n  db:\n    image: busybox:1.36\n",
            ["config", "--profiles"],
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_enabled_profile_does_not_filter_the_list(self) -> None:
        result = _run(COMPOSE, ["--profile", "alpha", "config", "--profiles"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "alpha\nmid\nzoo\n")
        self.assertEqual(result.stderr, "")

    def test_compose_profiles_env_does_not_filter_the_list(self) -> None:
        result = _run(COMPOSE, ["config", "--profiles"], {"COMPOSE_PROFILES": "zoo"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "alpha\nmid\nzoo\n")
        self.assertEqual(result.stderr, "")

    def test_quiet_still_prints_profiles(self) -> None:
        result = _run(COMPOSE, ["config", "--profiles", "--quiet"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "alpha\nmid\nzoo\n")

    def test_services_flag_wins(self) -> None:
        result = _run(COMPOSE, ["config", "--services", "--profiles"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "plain\n")

    def test_interpolates_profile_names(self) -> None:
        compose = (
            "services:\n"
            "  web:\n"
            "    image: busybox:1.36\n"
            "    profiles:\n"
            "      - ${PROF_NAME:-fallback}\n"
            "      - literal\n"
        )
        unset = _run(compose, ["config", "--profiles"])
        set_name = _run(compose, ["config", "--profiles"], {"PROF_NAME": "fromenv"})

        self.assertEqual(unset.returncode, 0, unset.stderr)
        self.assertEqual(unset.stdout, "fallback\nliteral\n")
        self.assertEqual(set_name.returncode, 0, set_name.stderr)
        self.assertEqual(set_name.stdout, "fromenv\nliteral\n")
