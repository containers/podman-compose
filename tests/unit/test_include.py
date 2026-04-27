# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from typing import Any
from unittest import mock

import yaml
from parameterized import parameterized

from podman_compose import PodmanCompose


class TestIncludeDict(unittest.TestCase):
    def setUp(self) -> None:
        self.test_files: list[str] = []
        self.podman_compose = PodmanCompose()
        self.podman_compose.global_args.file = ["test-compose-main.yaml"]
        self.podman_compose.global_args.project_name = "test_project"
        self.podman_compose.global_args.env_file = None
        self.podman_compose.global_args.profile = []
        self.podman_compose.global_args.in_pod = "false"

    def tearDown(self) -> None:
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)

    def write_yaml(self, name: str, content: dict[str, Any]) -> None:
        with open(name, "w", encoding="utf-8") as f:
            yaml.safe_dump(content, f)
        self.test_files.append(name)

    @parameterized.expand([
        ("string", ["./test-compose-include.yaml"], ["base_web"]),
        ("dict_path_string", [{"path": "./test-compose-include.yaml"}], ["base_web"]),
        (
            "dict_path_list",
            [{"path": ["./test-compose-include.yaml", "./test-compose-include-2.yaml"]}],
            ["base_web", "base_web-2"],
        ),
        ("empty", [{"path": []}], []),
    ])
    def test_parse_compose_file_include(
        self, name: str, include_value: list, expected_included_services: list
    ) -> None:
        include_content = {"services": {"base_web": {"image": "nginx:alpine"}}}
        self.write_yaml("test-compose-include.yaml", include_content)

        include_content_2 = {"services": {"base_web-2": {"image": "nginx:alpine"}}}
        self.write_yaml("test-compose-include-2.yaml", include_content_2)

        main_content = {
            "include": include_value,
            "services": {"web": {"image": "alpine:latest"}},
        }
        self.write_yaml("test-compose-main.yaml", main_content)

        self.podman_compose._parse_compose_file()

        self.assertIn("web", self.podman_compose.services)

        for svc in expected_included_services:
            self.assertIn(svc, self.podman_compose.services)

    @parameterized.expand([
        ("not_a_list", {"path": {"./test-compose-include.yaml"}}, "`include` must be a list"),
        (
            "no_path_key",
            [{"not_path": "./test-compose-include.yaml"}],
            "Missing required 'path' key in `include` block",
        ),
        ("path_not_list_or_string", [{"path": {}}], "'path' must be a string or a list of strings"),
        (
            "item_wrong_format",
            [["./test-compose-include.yaml"]],
            "Items in `include` must be strings or dictionaries with a 'path' key",
        ),
    ])
    def test_parse_compose_file_include_errors(
        self, name: str, include_value: dict | list, exception_msg: str
    ) -> None:
        main_content = {
            "include": include_value,
            "services": {"web": {"image": "alpine:latest"}},
        }
        self.write_yaml("test-compose-main.yaml", main_content)

        with self.assertRaises(RuntimeError) as cm:
            self.podman_compose._parse_compose_file()
        self.assertEqual(str(cm.exception), exception_msg)


def _set_args(podman_compose: PodmanCompose, file_names: list[str]) -> None:
    podman_compose.global_args = argparse.Namespace()
    podman_compose.global_args.file = file_names
    podman_compose.global_args.project_name = None
    podman_compose.global_args.env_file = None
    podman_compose.global_args.profile = []
    podman_compose.global_args.in_pod = "1"
    podman_compose.global_args.pod_args = None
    podman_compose.global_args.no_normalize = True


class TestResolveIncludeEntries(unittest.TestCase):
    def test_short_form_string(self) -> None:
        entries = PodmanCompose._resolve_include_entries(["other.yaml"], "/base")
        self.assertEqual(entries, [("/base/other.yaml", None)])

    def test_long_form_path_as_string(self) -> None:
        entries = PodmanCompose._resolve_include_entries([{"path": "other.yaml"}], "/base")
        self.assertEqual(entries, [("/base/other.yaml", None)])

    def test_long_form_path_as_list(self) -> None:
        entries = PodmanCompose._resolve_include_entries([{"path": ["a.yaml", "b.yaml"]}], "/base")
        self.assertEqual(
            entries,
            [("/base/a.yaml", None), ("/base/b.yaml", None)],
        )

    def test_long_form_rejects_missing_path(self) -> None:
        with self.assertRaises(RuntimeError):
            PodmanCompose._resolve_include_entries([{"env_file": "x.env"}], "/base")


class TestIncludeEnvFile(unittest.TestCase):
    """
    Exercises the `include` object form in podman-compose. Per the
    compose-spec, an include item may be a mapping with a `path` (string or
    list) and an optional `env_file` used to populate default values when
    interpolating variables in the included compose file. Shell environment
    takes precedence over env_file.
    """

    def _write(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_yaml(self, path: str, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def test_env_file_variables_used_for_interpolation_in_included_file(self) -> None:
        """
        Variables declared in include.env_file must be visible for variable
        interpolation when the included compose file is parsed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(tmpdir, "child.yaml")
            env_file = os.path.join(tmpdir, "my.env")
            self._write_yaml(
                parent,
                {"include": [{"path": "child.yaml", "env_file": "my.env"}]},
            )
            self._write(child, "services:\n  web:\n    image: ${IMAGE_NAME}\n")
            self._write(env_file, "IMAGE_NAME=from-env-file\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("IMAGE_NAME", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "from-env-file")

    def test_path_interpolation_uses_parent_environment(self) -> None:
        """
        Variable interpolation inside the `path` values of an include block
        is performed using the parent compose's environment.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "sub"))
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(tmpdir, "sub", "child.yaml")
            self._write_yaml(
                parent,
                {"include": [{"path": "${INCLUDE_SUBDIR}/child.yaml"}]},
            )
            self._write(child, "services:\n  web:\n    image: alpine:3\n")

            with mock.patch.dict(os.environ, {"INCLUDE_SUBDIR": "sub"}):
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "alpine:3")

    def test_env_file_internal_variable_interpolation(self) -> None:
        """
        dotenv-style files support ${VAR} interpolation inside the file
        itself, matching Docker's behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(tmpdir, "child.yaml")
            env_file = os.path.join(tmpdir, "my.env")
            self._write_yaml(
                parent,
                {"include": [{"path": "child.yaml", "env_file": "my.env"}]},
            )
            self._write(child, "services:\n  web:\n    image: ${IMAGE}\n")
            self._write(env_file, "BASE=alpine\nIMAGE=${BASE}:3.19\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("IMAGE", None)
                os.environ.pop("BASE", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "alpine:3.19")

    def test_shell_env_takes_precedence_over_env_file(self) -> None:
        """
        Per compose-spec: include.env_file provides default values for
        interpolation, but shell environment takes precedence.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(tmpdir, "child.yaml")
            env_file = os.path.join(tmpdir, "my.env")
            self._write_yaml(
                parent,
                {"include": [{"path": "child.yaml", "env_file": "my.env"}]},
            )
            self._write(child, "services:\n  web:\n    image: ${IMAGE_NAME}\n")
            self._write(env_file, "IMAGE_NAME=from-env-file\n")

            with mock.patch.dict(os.environ, {"IMAGE_NAME": "from-shell"}):
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "from-shell")

    def test_env_file_fills_missing_variables_without_replacing_others(self) -> None:
        """
        env_file is additive: variables NOT mentioned in env_file remain
        available for interpolation from the parent environment.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(tmpdir, "child.yaml")
            env_file = os.path.join(tmpdir, "my.env")
            self._write_yaml(
                parent,
                {"include": [{"path": "child.yaml", "env_file": "my.env"}]},
            )
            self._write(
                child,
                "services:\n"
                "  web:\n"
                "    image: ${IMAGE_NAME}\n"
                "    hostname: ${HOSTNAME_FROM_SHELL}\n",
            )
            self._write(env_file, "IMAGE_NAME=alpine:3.19\n")

            with mock.patch.dict(os.environ, {"HOSTNAME_FROM_SHELL": "shellhost"}):
                os.environ.pop("IMAGE_NAME", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "alpine:3.19")
            self.assertEqual(pc.services["web"]["hostname"], "shellhost")

    def test_default_env_file_is_loaded_from_included_project_directory(self) -> None:
        """
        Per compose-spec: when env_file is not declared on the include entry,
        it defaults to a `.env` file in the included file's project_directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "sub")
            os.makedirs(subdir)
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(subdir, "child.yaml")
            child_dotenv = os.path.join(subdir, ".env")
            self._write_yaml(parent, {"include": ["sub/child.yaml"]})
            self._write(child, "services:\n  web:\n    image: ${DEFAULT_IMAGE}\n")
            self._write(child_dotenv, "DEFAULT_IMAGE=default-from-child-env\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DEFAULT_IMAGE", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "default-from-child-env")

    def test_multiple_paths_share_env_file(self) -> None:
        """
        A single include entry may declare multiple paths; the env_file
        applies to every included file.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            a = os.path.join(tmpdir, "a.yaml")
            b = os.path.join(tmpdir, "b.yaml")
            env_file = os.path.join(tmpdir, "my.env")
            self._write_yaml(
                parent,
                {"include": [{"path": ["a.yaml", "b.yaml"], "env_file": "my.env"}]},
            )
            self._write(a, "services:\n  svc_a:\n    image: ${IMAGE_A}\n")
            self._write(b, "services:\n  svc_b:\n    image: ${IMAGE_B}\n")
            self._write(env_file, "IMAGE_A=alpine:1\nIMAGE_B=alpine:2\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("IMAGE_A", None)
                os.environ.pop("IMAGE_B", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["svc_a"]["image"], "alpine:1")
            self.assertEqual(pc.services["svc_b"]["image"], "alpine:2")
