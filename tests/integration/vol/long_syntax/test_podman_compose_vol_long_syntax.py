# SPDX-License-Identifier: GPL-2.0

import os
import shutil
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(test_ref_folder: str) -> str:
    return os.path.join(test_path(), "vol", test_ref_folder, "docker-compose.yml")


class TestComposeVolLongSyntax(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        (True, "create_host_path_default_true"),
        (True, "create_host_path_true"),
        (True, "create_host_path_false"),
        (False, "create_host_path_default_true"),
        (False, "create_host_path_true"),
    ])
    def test_source_host_dir(self, source_dir_exists: bool, service_name: str) -> None:
        project_dir = os.path.join(test_path(), "vol", "long_syntax")
        if source_dir_exists:
            # create host source directory for volume
            os.mkdir(os.path.join(project_dir, "test_dir"))
        else:
            # make sure there is no such directory
            self.assertFalse(os.path.isdir(os.path.join(project_dir, "test_dir")))

        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path("long_syntax"),
                    "up",
                    "-d",
                    f"{service_name}",
                ],
                0,
            )
            # command of the service creates a new directory on mounted directory 'test_dir' in
            # the container. Check if host directory now has the same directory. It represents a
            # successful mount.
            # If source host directory does not exist, it is created
            self.assertTrue(os.path.isdir(os.path.join(project_dir, "test_dir/new_dir")))

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("long_syntax"),
                "down",
                "-t",
                "0",
            ])
            shutil.rmtree(os.path.join(project_dir, "test_dir"))

    def test_no_host_source_dir_create_host_path_false(self) -> None:
        try:
            _, error = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path("long_syntax"),
                    "up",
                    "-d",
                    "create_host_path_false",
                ],
                1,
            )
            self.assertIn(
                b"invalid mount config for type 'bind': bind source path does not exist:", error
            )
        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path("long_syntax"),
                "down",
                "-t",
                "0",
            ])
