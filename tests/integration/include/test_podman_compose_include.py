# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from typing import Optional

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(suffix: str = "") -> str:
    return os.path.join(os.path.join(test_path(), "include"), f"docker-compose{suffix}.yaml")


def env_file_fixture(*parts: str) -> str:
    return os.path.join(test_path(), "include", "env_file", *parts)


def project_directory_fixture(*parts: str) -> str:
    return os.path.join(test_path(), "include", "project_directory", *parts)


class TestPodmanComposeInclude(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ("string", ""),
        ("dict", "_include_dict"),
    ])
    def test_podman_compose_include(self, name: str, compose_suffix: str) -> None:
        try:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                compose_yaml_path(f"{compose_suffix}"),
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "ps",
                "-a",
                "--filter",
                "label=io.podman.compose.project=include",
                "--format",
                '"{{.Names}}"',
            ])
            # two services from included compose files were created
            self.assertEqual(out, b'"include_web_1"\n"include_web2_1"\n')
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])


class TestPodmanComposeIncludeEnvFile(unittest.TestCase, RunSubprocessMixin):
    """Cover the `include[].env_file` semantics via the `config` subcommand."""

    def _config(
        self,
        compose_file: str,
        env: Optional[dict[str, str]] = None,
        expected_returncode: int = 0,
    ) -> tuple[str, str]:
        cmd = [podman_compose_path(), "-f", compose_file, "config"]
        out, err = self.run_subprocess_assert_returncode(
            cmd, expected_returncode=expected_returncode, env=env or {}
        )
        return out.decode("utf-8"), err.decode("utf-8")

    def test_explicit_env_file_is_loaded_for_included_file(self) -> None:
        """Variables from an include's explicit env_file feed the included file's interpolation."""
        out, _ = self._config(env_file_fixture("explicit", "docker-compose.yaml"))
        self.assertIn("image: localhost/child-from-env-file", out)

    def test_default_dotenv_next_to_included_file_is_loaded(self) -> None:
        """When env_file is unset, `.env` next to the included file is picked up automatically."""
        out, _ = self._config(env_file_fixture("default-dotenv", "docker-compose.yaml"))
        self.assertIn("image: localhost/alpine-default", out)

    def test_multiple_env_files_later_overrides_earlier(self) -> None:
        """A list of env_files merges left-to-right — later files override earlier ones,
        but values only present in earlier files are preserved."""
        out, _ = self._config(env_file_fixture("multi", "docker-compose.yaml"))
        self.assertIn("image: localhost/alpine-override", out)
        self.assertNotIn("alpine-base", out)
        self.assertIn("base: keep-me", out)

    def test_missing_explicit_env_file_raises(self) -> None:
        """An env_file path that doesn't resolve to a real file is a hard error,
        not a silent empty load."""
        _, err = self._config(
            env_file_fixture("missing", "docker-compose.yaml"),
            expected_returncode=1,
        )
        self.assertIn("nope.env", err)
        self.assertIn("not found", err)

    def test_env_file_does_not_leak_into_parent_compose(self) -> None:
        """An include's env_file applies only to that included file's interpolation;
        the parent compose file resolves variables from its own (shell + project .env) env."""
        out, _ = self._config(env_file_fixture("explicit", "docker-compose.yaml"))
        self.assertIn("image: localhost/parent-fallback", out)
        self.assertNotIn("parent-from-env-file", out)

    def test_shell_environment_overrides_include_env_file(self) -> None:
        """Compose-spec semantics: env_file values are defaults; the surrounding
        environment (shell + project .env) wins on conflict."""
        out, _ = self._config(
            env_file_fixture("explicit", "docker-compose.yaml"),
            env={"INCLUDE_ENVFILE_LEAK_VAR": "from-shell"},
        )
        self.assertIn("image: localhost/child-from-shell", out)
        self.assertIn("image: localhost/parent-from-shell", out)
        self.assertNotIn("from-env-file", out)


class TestPodmanComposeIncludeProjectDirectory(unittest.TestCase, RunSubprocessMixin):
    """Cover the `include[].project_directory` semantics via the `config` subcommand."""

    def _config(self, compose_file: str) -> str:
        out, _ = self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_file,
            "config",
        ])
        return out.decode("utf-8")

    def test_default_project_directory_is_included_file_directory(self) -> None:
        """When project_directory is omitted, default `.env` lookup uses the
        included file's directory — matching the compose-spec default."""
        out = self._config(project_directory_fixture("default", "docker-compose.yaml"))
        self.assertIn("image: localhost/from-included-dir", out)

    def test_explicit_project_directory_relocates_default_dotenv(self) -> None:
        """An explicit `project_directory` overrides where the default `.env`
        is looked up: the .env next to the included file must be ignored, and
        the one inside project_directory used instead."""
        out = self._config(project_directory_fixture("explicit", "docker-compose.yaml"))
        self.assertIn("image: localhost/from-project-dir", out)
        self.assertNotIn("wrong-from-child-dir", out)

    def test_explicit_env_file_resolved_relative_to_parent_not_project_directory(self) -> None:
        """`project_directory` only relocates the *default* .env lookup. When an
        explicit `env_file` is set, its path is resolved relative to the parent
        compose's directory — matching docker compose behavior."""
        out = self._config(project_directory_fixture("explicit-env-file", "docker-compose.yaml"))
        self.assertIn("image: localhost/from-base-dir", out)
        self.assertNotIn("wrong-from-project-dir", out)

    def test_nested_include_uses_default_project_directory_of_each_level(self) -> None:
        """When an included compose file itself uses ``include``, each level's
        default `.env` lookup uses the directory of that level's included file.
        Here parent → mid/mid.yaml → mid/leaf/leaf.yaml: leaf's default .env is
        ``mid/leaf/.env`` (its own directory), not ``mid/.env`` or the parent's."""
        out = self._config(project_directory_fixture("nested-default", "docker-compose.yaml"))
        self.assertIn("image: localhost/from-leaf-dir", out)

    def test_nested_include_inherits_parent_include_env(self) -> None:
        """Variables loaded for an included file (from its env_file or default
        `.env`) stay visible inside that file's own nested includes, matching
        docker compose. Here parent → mid/mid.yaml → mid/leaf/leaf.yaml: leaf
        has no `.env` of its own but still sees ``mid/.env``."""
        out = self._config(project_directory_fixture("nested-inherit", "docker-compose.yaml"))
        self.assertIn("image: localhost/from-mid-env", out)
        self.assertNotIn("localhost/unset", out)

    def test_nested_include_resolves_project_directory_against_inner_parent(self) -> None:
        """A relative ``project_directory`` in a nested include must be resolved
        against the *enclosing* compose file's project_directory, not against
        the directory holding that compose file. Here ``mid.yaml`` is included
        with ``project_directory: top_alt`` and itself declares
        ``project_directory: inner_alt`` for its own include of ``leaf.yaml``.
        The leaf's default `.env` must be ``top_alt/inner_alt/.env`` — not
        ``top_alt/leaf/.env`` (which would mean inner ``project_directory``
        was ignored) and not ``mid/inner_alt/.env`` (which would mean inner
        ``project_directory`` was resolved against mid's directory instead of
        mid's own ``project_directory``).

        Divergence from docker compose: docker compose (5.1.0) does not load a
        default `.env` for a nested include that has an explicit *relative*
        ``project_directory`` — the leaf renders as ``localhost/unset``. This
        test pins podman-compose's stricter behavior of honoring the spec for
        nested resolution; rendered output for this fixture will not match
        ``docker compose config``."""
        out = self._config(project_directory_fixture("nested-explicit", "docker-compose.yaml"))
        self.assertIn("image: localhost/from-mid-alt", out)
        self.assertNotIn("wrong-from-leaf-dir", out)
        self.assertNotIn("wrong-from-mid-inner-alt", out)

    def test_top_level_project_directory_relocates_included_file_dotenv(self) -> None:
        """A ``project_directory`` declared on the *top-level* include relocates
        the default `.env` lookup for the included file. Here ``mid.yaml`` has
        its own ``mid/.env`` (the default location) but the top-level include
        declares ``project_directory: top_alt``, so ``top_alt/.env`` wins. The
        midservice's image carries the value of ``TOP_PROJDIR_VAR`` from
        whichever .env was actually loaded, pinning the resolution rule."""
        out = self._config(project_directory_fixture("nested-explicit", "docker-compose.yaml"))
        self.assertIn("image: localhost/mid-from-toplevel-projdir", out)
        self.assertNotIn("mid-wrong-from-mid-default", out)
        self.assertNotIn("mid-unset", out)

    def test_project_directory_rebases_extends_file(self) -> None:
        """``extends.file`` inside an included compose file is a relative path
        set "inside the Compose file", so it must resolve against the include's
        ``project_directory`` (here ``alt/``), not against the included file's
        own directory (``mid/``). After extends-merge the service's image must
        be the one from ``alt/base.yaml``, not the ``mid/base.yaml`` decoy."""
        fixture_dir = project_directory_fixture("extends-projdir")
        out = self._config(os.path.join(fixture_dir, "docker-compose.yaml"))
        self.assertIn("image: localhost/from-alt-base", out)
        self.assertNotIn("wrong-from-mid-base", out)

    def test_project_directory_rebases_relative_paths_inside_included_file(self) -> None:
        """``project_directory`` is the base for resolving relative paths
        *inside* the included file — not just for the default .env lookup.
        Here mid.yaml's nested ``include: leaf/leaf.yaml`` resolves to
        ``top_alt/leaf/leaf.yaml`` (mid's project_directory), not to
        ``mid/leaf/leaf.yaml`` (mid's own directory). If the leaf service
        appears in the rendered config at all, the path was resolved under
        ``top_alt/`` — matching docker compose's behavior."""
        out = self._config(project_directory_fixture("nested-explicit", "docker-compose.yaml"))
        self.assertIn("nestedexplicitleaf:", out)
