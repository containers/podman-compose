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
    compose: str,
    args: list[str],
    env: dict[str, str] | None = None,
    extra_files: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "compose.yml"
        path.write_text(compose, encoding="utf-8")
        for name, content in (extra_files or {}).items():
            (Path(tmp) / name).write_text(content, encoding="utf-8")
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


LISTS = """\
services:
  web:
    image: nginx:1.27
    networks: [front]
    volumes: [data:/data, ./src:/src]
  builder:
    build: .
    networks: [front]
  tool:
    image: alpine
    profiles: [tools]
    networks: [front]
    volumes: [cache:/cache]
volumes:
  data:
  cache:
  unused:
networks:
  front:
"""


class TestComposeConfigLists(unittest.TestCase):
    def test_services_ignore_quiet(self) -> None:
        result = _run(LISTS, ["config", "--services", "--quiet"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "web\nbuilder\n")

    def test_images_of_active_services(self) -> None:
        result = _run(LISTS, ["config", "--images"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "nginx:1.27\nprofiles-test_builder\n")

    def test_images_follow_enabled_profile(self) -> None:
        result = _run(LISTS, ["--profile", "tools", "config", "--images"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "nginx:1.27\nprofiles-test_builder\nalpine\n")

    def test_volumes_used_by_active_services(self) -> None:
        result = _run(LISTS, ["config", "--volumes"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "data\n")

    def test_volumes_follow_enabled_profile(self) -> None:
        result = _run(LISTS, ["--profile", "tools", "config", "--volumes"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "data\ncache\n")

    def test_networks_used_by_active_services(self) -> None:
        result = _run(LISTS, ["config", "--networks"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "front\n")

    def test_volumes_win_over_networks_profiles_and_images(self) -> None:
        result = _run(
            LISTS, ["config", "--images", "--profiles", "--networks", "--volumes", "--quiet"]
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "data\n")

    def test_profiles_win_over_images(self) -> None:
        result = _run(LISTS, ["config", "--images", "--profiles"])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "tools\n")

    def test_networks_skip_network_mode(self) -> None:
        result = _run(
            "services:\n"
            "  hostnet:\n"
            "    image: busybox\n"
            "    network_mode: host\n"
            "networks:\n"
            "  front: {}\n",
            ["config", "--networks"],
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_images_and_volumes_include_services_scaled_to_zero(self) -> None:
        compose = (
            "services:\n"
            "  web:\n"
            "    image: nginx:1.27\n"
            "    volumes: [webdata:/data]\n"
            "  worker:\n"
            "    image: busybox:1.36\n"
            "    scale: 0\n"
            "    volumes: [workerdata:/data]\n"
            "volumes:\n"
            "  webdata: {}\n"
            "  workerdata: {}\n"
        )
        images = _run(compose, ["config", "--images"])
        volumes = _run(compose, ["config", "--volumes"])

        self.assertEqual(images.returncode, 0, images.stderr)
        self.assertEqual(images.stdout, "nginx:1.27\nbusybox:1.36\n")
        self.assertEqual(volumes.returncode, 0, volumes.stderr)
        self.assertEqual(volumes.stdout, "webdata\nworkerdata\n")

    def test_profiles_include_extends_file_base(self) -> None:
        result = _run(
            "services:\n"
            "  child:\n"
            "    extends:\n"
            "      file: common.yml\n"
            "      service: base\n"
            "  plain:\n"
            "    image: alpine\n",
            ["config", "--profiles"],
            extra_files={
                "common.yml": "services:\n  base:\n    image: busybox\n    profiles: [ext]\n"
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ext\n")

    def test_profiles_follow_chain_inside_extends_file(self) -> None:
        result = _run(
            "services:\n"
            "  c:\n"
            "    extends:\n"
            "      file: base.yml\n"
            "      service: b\n"
            "  d:\n"
            "    image: alpine\n",
            ["config", "--profiles"],
            extra_files={
                "base.yml": "services:\n"
                "  root:\n"
                "    image: busybox\n"
                "    profiles: [deep]\n"
                "  b:\n"
                "    extends: root\n"
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "deep\n")

    def test_other_commands_skip_extends_file_of_inactive_service(self) -> None:
        compose = (
            "services:\n"
            "  app:\n"
            "    image: alpine\n"
            "  debug:\n"
            "    profiles: [debug]\n"
            "    extends:\n"
            "      file: debug.yml\n"
            "      service: dbg\n"
        )
        debug = (
            "services:\n  dbg:\n    image: busybox\n    environment:\n      T: ${NEEDED:?unset}\n"
        )
        result = _run(compose, ["config", "--services"], extra_files={"debug.yml": debug})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "app\n")
