# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_base_path() -> str:
    return os.path.join(test_path(), "env_file_tests")


class TestComposeEnvFile(unittest.TestCase, RunSubprocessMixin):
    def test_path_env_file_inline(self) -> None:
        # Test taking env variable value directly from env-file when its path is inline path
        base_path = compose_base_path()
        path_compose_file = os.path.join(base_path, "project/container-compose.yaml")
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "--env-file",
                os.path.join(base_path, "env-files/project-1.env"),
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "logs",
            ])
            # takes only value ZZVAR1 as container-compose.yaml file requires
            self.assertEqual(output, b"ZZVAR1=podman-rocks-123\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])

    def test_path_env_file_flat_in_compose_file(self) -> None:
        # Test taking env variable value from env-file/project-1.env which was declared in
        # compose file's env_file
        base_path = compose_base_path()
        path_compose_file = os.path.join(base_path, "project/container-compose.env-file-flat.yaml")
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "logs",
            ])
            # takes all values with a substring ZZ as container-compose.env-file-flat.yaml
            # file requires
            self.assertEqual(
                output,
                b"ZZVAR1=podman-rocks-123\nZZVAR2=podman-rocks-124\nZZVAR3=podman-rocks-125\n",
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])

    def test_path_env_file_obj_in_compose_file(self) -> None:
        # take variable value from env-file project-1.env which was declared in compose
        # file's env_file by -path: ...
        base_path = compose_base_path()
        path_compose_file = os.path.join(base_path, "project/container-compose.env-file-obj.yaml")
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "logs",
            ])
            # takes all values with a substring ZZ as container-compose.env-file-obj.yaml
            # file requires
            self.assertEqual(
                output,
                b"ZZVAR1=podman-rocks-123\nZZVAR2=podman-rocks-124\nZZVAR3=podman-rocks-125\n",
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])

    def test_exists_optional_env_file_path_in_compose_file(self) -> None:
        # test taking env variable values from several env-files when one of them is optional
        # and exists
        base_path = compose_base_path()
        path_compose_file = os.path.join(
            base_path, "project/container-compose.env-file-obj-optional-exists.yaml"
        )
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "logs",
            ])
            # FIXME: gives a weird output, needs to be double checked
            self.assertEqual(
                output,
                b"ZZVAR1=podman-rocks-223\nZZVAR2=podman-rocks-224\nZZVAR3=podman-rocks-125\n",
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])

    def test_missing_optional_env_file_path_in_compose_file(self) -> None:
        # test taking env variable values from several env-files when one of them is optional and
        # is missing (silently skip it)
        base_path = compose_base_path()
        path_compose_file = os.path.join(
            base_path, "project/container-compose.env-file-obj-optional-missing.yaml"
        )
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "logs",
            ])
            # takes all values with a substring ZZ as container-compose.env-file-obj-optional.yaml
            # file requires
            self.assertEqual(
                output,
                b"ZZVAR1=podman-rocks-123\nZZVAR2=podman-rocks-124\nZZVAR3=podman-rocks-125\n",
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])

    def test_var_value_inline_overrides_env_file_path_inline(self) -> None:
        # Test overriding env value when value is declared in inline command
        base_path = compose_base_path()
        path_compose_file = os.path.join(base_path, "project/container-compose.yaml")
        try:
            self.run_subprocess_assert_returncode([
                "env",
                "ZZVAR1=podman-rocks-321",
                podman_compose_path(),
                "-f",
                path_compose_file,
                "--env-file",
                os.path.join(base_path, "env-files/project-1.env"),
                "up",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "logs",
            ])
            # takes only value ZZVAR1 as container-compose.yaml file requires
            self.assertEqual(output, b"ZZVAR1=podman-rocks-321\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])

    def test_taking_env_variables_from_env_files_from_different_directories(self) -> None:
        # FIXME: It is not clear what this test actually tests, but from README.md it looks like:
        # Test overriding env values by directory env-files-tests/.env file values
        # and only take value from project/.env, when it does not exist in env-files-tests/.env
        base_path = compose_base_path()
        path_compose_file = os.path.join(
            base_path, "project/container-compose.load-.env-in-project.yaml"
        )
        try:
            # looks like 'run' command does not actually create a container, so output_logs can not
            # be used for test comparison
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "run",
                "--rm",
                "app",
            ])
            # takes all values with a substring ZZ as container-compose.load-.env-in-project.yaml
            # file requires
            # first line is random ID so is ignored in asserting
            lines = output.decode('utf-8').split('\n')[1:]

            self.assertEqual(
                lines,
                [
                    'ZZVAR1=This value is loaded but should be overwritten\r',
                    'ZZVAR2=This value is loaded from .env in project/ directory\r',
                    'ZZVAR3=TEST\r',
                    '',
                ],
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path_compose_file,
                "down",
            ])

    def test_env_var_value_accessed_in_compose_file_short_syntax(self) -> None:
        # Test that compose file can access the environment variable set in .env file using
        # short syntax, that is: only the name of environment variable is used in "environment:" in
        # compose.yml file and its value is picked up directly from .env file
        # long syntax of environment variables interpolation is tested in
        # tests/integration/interpolation

        base_path = compose_base_path()
        compose_file_path = os.path.join(base_path, "project/container-compose.short_syntax.yaml")
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file_path,
                "up",
                "-d",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file_path,
                "logs",
            ])
            # ZZVAR3 was set in .env file
            self.assertEqual(output, b"ZZVAR3=TEST\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file_path,
                "down",
            ])
