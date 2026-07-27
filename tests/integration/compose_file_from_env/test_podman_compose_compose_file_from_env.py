# SPDX-License-Identifier: GPL-2.0

import unittest
from pathlib import Path

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path


def compose_base_path() -> Path:
    return Path(__file__).parent


class TestComposeFileFromEnv(unittest.TestCase, RunSubprocessMixin):
    """Test that COMPOSE_FILE from .env is honored when no -f is given."""

    def test_compose_file_from_dotenv(self) -> None:
        base_path = compose_base_path()
        out, _ = self.run_subprocess_assert_returncode(
            [podman_compose_path(), "config"],
            0,
            cwd=base_path,
        )
        self.assertEqual(
            out.decode("utf-8"),
            'services:\n'
            '  dotenv-service:\n'
            '    command: echo "from-dotenv"\n'
            '    image: nopush/podman-compose-test\n'
            '\n',
        )

    def test_compose_file_from_explicit_env_file(self) -> None:
        base_path = compose_base_path()

        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "--env-file",
                str(base_path / "custom.env"),
                "config",
            ],
            0,
            cwd=base_path,
        )
        self.assertEqual(
            out.decode("utf-8"),
            'services:\n'
            '  explicit-env-service:\n'
            '    command: echo "from-explicit-env"\n'
            '    image: nopush/podman-compose-test\n'
            '\n',
        )

    def test_explicit_f_overrides_compose_file_from_dotenv(self) -> None:
        base_path = compose_base_path()
        explicit_compose_file = base_path / "docker-compose-explicit.yml"

        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                str(explicit_compose_file),
                "config",
            ],
            0,
            cwd=base_path,
        )
        self.assertEqual(
            out.decode("utf-8"),
            'services:\n'
            '  explicit-service:\n'
            '    command: echo "explicit"\n'
            '    image: nopush/podman-compose-test\n'
            '\n',
        )

    def test_env_var_compose_file_takes_precedence_over_dotenv(self) -> None:
        base_path = compose_base_path()

        out, _ = self.run_subprocess_assert_returncode(
            [podman_compose_path(), "config"],
            0,
            env={"COMPOSE_FILE": str(base_path / "docker-compose-var.yml")},
            cwd=base_path,
        )
        self.assertEqual(
            out.decode("utf-8"),
            'services:\n'
            '  var-service:\n'
            '    command: echo "var"\n'
            '    image: nopush/podman-compose-test\n'
            '\n',
        )

    def test_missing_env_file_from_flag_fails(self) -> None:
        base_path = compose_base_path()

        _, err = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "--env-file",
                str(base_path / "missing.env"),
                "config",
            ],
            1,
            cwd=base_path,
        )
        self.assertIn(b"Couldn't find env file", err)
