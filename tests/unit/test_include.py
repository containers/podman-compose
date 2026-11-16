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
        self.assertEqual(entries, [("/base/other.yaml", None, "/base")])

    def test_long_form_path_as_string(self) -> None:
        entries = PodmanCompose._resolve_include_entries([{"path": "other.yaml"}], "/base")
        self.assertEqual(entries, [("/base/other.yaml", None, "/base")])

    def test_long_form_path_as_list(self) -> None:
        entries = PodmanCompose._resolve_include_entries([{"path": ["a.yaml", "b.yaml"]}], "/base")
        self.assertEqual(
            entries,
            [("/base/a.yaml", None, "/base"), ("/base/b.yaml", None, "/base")],
        )

    def test_long_form_rejects_missing_path(self) -> None:
        with self.assertRaises(RuntimeError):
            PodmanCompose._resolve_include_entries([{"env_file": "x.env"}], "/base")

    def test_rejects_non_string_project_directory(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "project_directory"):
            PodmanCompose._resolve_include_entries(
                [{"path": "other.yaml", "project_directory": ["a", "b"]}], "/base"
            )

    def test_project_directory_resolved_relative_to_base_dir(self) -> None:
        """An explicit ``project_directory`` is resolved against ``base_dir``
        (the directory of the file containing the include directive)."""
        entries = PodmanCompose._resolve_include_entries(
            [{"path": "sub/other.yaml", "project_directory": "proj"}], "/base"
        )
        self.assertEqual(entries, [("/base/sub/other.yaml", None, "/base/proj")])


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

    def test_project_directory_relocates_default_dotenv_lookup(self) -> None:
        """
        Per compose-spec: ``include.project_directory`` overrides the base
        directory used to find the default `.env` for the included file.
        With project_directory set, the default .env is `<project_directory>/.env`
        rather than `<dir-of-included-file>/.env`.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            child_dir = os.path.join(tmpdir, "child_dir")
            project_dir = os.path.join(tmpdir, "proj_dir")
            os.makedirs(child_dir)
            os.makedirs(project_dir)
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(child_dir, "child.yaml")
            self._write_yaml(
                parent,
                {"include": [{"path": "child_dir/child.yaml", "project_directory": "proj_dir"}]},
            )
            self._write(child, "services:\n  web:\n    image: ${PD_IMG}\n")
            # .env next to the included file must be IGNORED when project_directory is set;
            # only the .env in project_directory should be read.
            self._write(os.path.join(child_dir, ".env"), "PD_IMG=wrong-child-dir\n")
            self._write(os.path.join(project_dir, ".env"), "PD_IMG=right-project-dir\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("PD_IMG", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "right-project-dir")

    def test_project_directory_default_is_included_file_directory(self) -> None:
        """
        When ``project_directory`` is omitted, the default .env lookup base is
        the directory of the included Compose file — which is also what the
        env_file feature already does. This test pins that as the spec default.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            child_dir = os.path.join(tmpdir, "child_dir")
            os.makedirs(child_dir)
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(child_dir, "child.yaml")
            self._write_yaml(parent, {"include": ["child_dir/child.yaml"]})
            self._write(child, "services:\n  web:\n    image: ${PD_DEFAULT}\n")
            # A decoy .env right next to the parent must NOT be used as the include
            # default — only child_dir/.env. Pass an explicit, unrelated --env-file so
            # the decoy is not loaded as the project .env (which would legitimately
            # take precedence over include defaults).
            self._write(os.path.join(tmpdir, ".env"), "PD_DEFAULT=from-parent-dir\n")
            self._write(os.path.join(child_dir, ".env"), "PD_DEFAULT=from-child-dir\n")
            unrelated_env = os.path.join(tmpdir, "unrelated.env")
            self._write(unrelated_env, "UNRELATED=1\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("PD_DEFAULT", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc.global_args.env_file = [unrelated_env]
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "from-child-dir")

    def test_nested_include_inherits_parent_include_env_file(self) -> None:
        """
        Like docker compose, variables from an include's env_file (or default
        .env) stay visible for interpolation inside that file's own nested
        includes, even when the nested include has no env_file of its own.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mid_dir = os.path.join(tmpdir, "mid")
            leaf_dir = os.path.join(mid_dir, "leaf")
            os.makedirs(leaf_dir)
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            mid = os.path.join(mid_dir, "mid.yaml")
            leaf = os.path.join(leaf_dir, "leaf.yaml")
            self._write_yaml(parent, {"include": ["mid/mid.yaml"]})
            self._write_yaml(mid, {"include": ["leaf/leaf.yaml"]})
            self._write(os.path.join(mid_dir, ".env"), "INHERIT_VAR=from-mid-env\n")
            self._write(leaf, "services:\n  web:\n    image: ${INHERIT_VAR:-unset}\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("INHERIT_VAR", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "from-mid-env")

    def test_nested_include_own_env_file_overrides_inherited(self) -> None:
        """
        A nested include's own env_file (or default .env) is layered on top of
        the variables inherited from the parent include.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mid_dir = os.path.join(tmpdir, "mid")
            leaf_dir = os.path.join(mid_dir, "leaf")
            os.makedirs(leaf_dir)
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            mid = os.path.join(mid_dir, "mid.yaml")
            leaf = os.path.join(leaf_dir, "leaf.yaml")
            self._write_yaml(parent, {"include": ["mid/mid.yaml"]})
            self._write_yaml(mid, {"include": ["leaf/leaf.yaml"]})
            self._write(os.path.join(mid_dir, ".env"), "BOTH=from-mid\nONLY_MID=mid\n")
            self._write(os.path.join(leaf_dir, ".env"), "BOTH=from-leaf\n")
            self._write(
                leaf,
                "services:\n  web:\n    image: ${BOTH}\n    hostname: ${ONLY_MID}\n",
            )

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BOTH", None)
                os.environ.pop("ONLY_MID", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "from-leaf")
            self.assertEqual(pc.services["web"]["hostname"], "mid")

    def test_project_directory_rebases_extends_file(self) -> None:
        """An ``extends.file`` path inside an included compose file must be
        resolved against the include's ``project_directory`` — not against the
        directory of the file containing the ``extends`` block. After the
        extends merge, the deriving service should carry the image declared
        in the file under ``project_directory/``, not the decoy in the
        included file's own directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            #   parent.yaml         (top, includes mid.yaml with project_directory=proj)
            #   mid/mid.yaml        (extends webapp from base.yaml)
            #   mid/base.yaml       (decoy — must NOT be used)
            #   proj/base.yaml      (correct — project_directory's base.yaml)
            os.makedirs(os.path.join(tmpdir, "mid"))
            os.makedirs(os.path.join(tmpdir, "proj"))
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            mid = os.path.join(tmpdir, "mid", "mid.yaml")
            decoy_base = os.path.join(tmpdir, "mid", "base.yaml")
            correct_base = os.path.join(tmpdir, "proj", "base.yaml")
            self._write_yaml(
                parent,
                {"include": [{"path": "mid/mid.yaml", "project_directory": "proj"}]},
            )
            self._write_yaml(
                mid,
                {
                    "services": {
                        "derived": {
                            "extends": {"file": "base.yaml", "service": "webapp"},
                        }
                    }
                },
            )
            self._write(decoy_base, "services:\n  webapp:\n    image: wrong-from-mid\n")
            self._write(correct_base, "services:\n  webapp:\n    image: from-proj\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["derived"]["image"], "from-proj")

    def test_project_directory_rebases_nested_include_path(self) -> None:
        """``project_directory`` is the base for resolving relative paths
        *inside* the included file — including nested ``include[].path``
        entries. So with ``project_directory: proj`` on a top-level include
        of ``mid.yaml``, any relative include path inside ``mid.yaml``
        resolves against ``proj/``, not against the directory holding
        ``mid.yaml``. This matches docker compose's behavior."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Layout:
            #   parent.yaml
            #   mid/mid.yaml           -- included via project_directory: proj
            #   proj/leaf/leaf.yaml    -- mid's nested `include: leaf/leaf.yaml`
            #                              must resolve under proj/, not mid/
            os.makedirs(os.path.join(tmpdir, "mid"))
            os.makedirs(os.path.join(tmpdir, "proj", "leaf"))
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            mid = os.path.join(tmpdir, "mid", "mid.yaml")
            leaf = os.path.join(tmpdir, "proj", "leaf", "leaf.yaml")
            self._write_yaml(
                parent,
                {"include": [{"path": "mid/mid.yaml", "project_directory": "proj"}]},
            )
            self._write_yaml(mid, {"include": ["leaf/leaf.yaml"]})
            self._write(leaf, "services:\n  leaf:\n    image: nested-leaf\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["leaf"]["image"], "nested-leaf")

    def test_explicit_env_file_ignores_project_directory(self) -> None:
        """
        ``project_directory`` only relocates the *default* .env lookup. When
        an explicit ``env_file`` is supplied, its path is resolved relative to
        the parent compose's directory — matching docker compose behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            child_dir = os.path.join(tmpdir, "child_dir")
            project_dir = os.path.join(tmpdir, "proj_dir")
            os.makedirs(child_dir)
            os.makedirs(project_dir)
            parent = os.path.join(tmpdir, "docker-compose.yaml")
            child = os.path.join(child_dir, "child.yaml")
            self._write_yaml(
                parent,
                {
                    "include": [
                        {
                            "path": "child_dir/child.yaml",
                            "project_directory": "proj_dir",
                            "env_file": "extra.env",
                        }
                    ]
                },
            )
            self._write(child, "services:\n  web:\n    image: ${PD_EXPLICIT}\n")
            # env_file: extra.env, resolved relative to parent compose's dir, not project_directory.
            self._write(os.path.join(tmpdir, "extra.env"), "PD_EXPLICIT=right-parent-dir\n")
            self._write(os.path.join(project_dir, "extra.env"), "PD_EXPLICIT=wrong-project-dir\n")

            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("PD_EXPLICIT", None)
                pc = PodmanCompose()
                _set_args(pc, [parent])
                pc._parse_compose_file()  # pylint: disable=protected-access

            self.assertEqual(pc.services["web"]["image"], "right-parent-dir")

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
