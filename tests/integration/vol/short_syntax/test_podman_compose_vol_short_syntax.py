# SPDX-License-Identifier: GPL-2.0

import json
import os
import shutil
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(test_ref_folder: str) -> str:
    return os.path.join(test_path(), "vol", test_ref_folder, "docker-compose.yml")


class TestComposeVolShortSyntax(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        (True, "test1"),
        (False, "test2"),
    ])
    def test_source_host_dir(self, source_host_dir_exists: bool, service_name: str) -> None:
        project_dir = os.path.join(test_path(), "vol", "short_syntax")
        # create host source directory for volume
        if source_host_dir_exists:
            os.mkdir(os.path.join(project_dir, "test_dir"))
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path("short_syntax"),
                    "up",
                    "-d",
                    f"{service_name}",
                ],
                0,
            )
            # command of the service creates a new directory on mounted directory 'test_dir' in
            # container. Check if host directory now has the same directory. It represents a
            # successful mount.
            # On service test2 source host directory is created as it did not exist
            self.assertTrue(os.path.isdir(os.path.join(project_dir, "test_dir/new_dir")))

        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path("short_syntax"),
                "down",
                "-t",
                "0",
            ])
            shutil.rmtree(os.path.join(project_dir, "test_dir"))

    def test_volume_source_is_symlink(self) -> None:
        try:
            base = "/tmp/symlink-test"
            real_dir = os.path.join(base, "real")
            link_dir = os.path.join(base, "link")

            os.makedirs(real_dir, exist_ok=True)

            os.symlink(real_dir, link_dir)

            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path("short_syntax"),
                    "up",
                    "-d",
                ],
                0,
            )

            out, _ = self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "inspect",
                    "short_syntax_test3_1",
                ],
                0,
            )

            container_info = json.loads(out)
            bind_string = container_info[0].get("HostConfig", {}).get("Binds")[0]
            # podman-compose should not dereference the symlink directory
            self.assertEqual(bind_string.split(":", 1)[0], link_dir)
        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_yaml_path("short_syntax"),
                "down",
                "-t",
                "0",
            ])
            shutil.rmtree(base, ignore_errors=True)
