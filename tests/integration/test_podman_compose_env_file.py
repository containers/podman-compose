# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_base_path():
    return os.path.join(test_path(), "env-file-tests")


class TestComposeEnvFile(unittest.TestCase, RunSubprocessMixin):
    def test_path_env_file_inline(self):
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

    def test_path_env_file_flat_in_compose_file(self):
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

    def test_path_env_file_obj_in_compose_file(self):
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

    def test_exists_optional_env_file_path_in_compose_file(self):
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

    def test_missing_optional_env_file_path_in_compose_file(self):
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

    def test_var_value_inline_overrides_env_file_path_inline(self):
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

    def test_taking_env_variables_from_env_files_from_different_directories(self):
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
                    'ZZVAR3=$ZZVAR3\r',
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
