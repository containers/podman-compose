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
