# SPDX-License-Identifier: GPL-2.0


import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


class TestFilesystem(unittest.TestCase, RunSubprocessMixin):
    def test_compose_symlink(self):
        """The context of podman-compose.yml should come from the same directory as the file even
        if it is a symlink
        """

        compose_path = os.path.join(test_path(), "filesystem/compose_symlink/docker-compose.yml")

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
                "container1",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
                "container1",
            ])

            # BUG: figure out why cat is called twice
            self.assertEqual(out, b'data_compose_symlink\ndata_compose_symlink\n')

        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])
