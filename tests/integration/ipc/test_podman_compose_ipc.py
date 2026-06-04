# SPDX-License-Identifier: GPL-2.0

"""Test passing of ipc mode to podman."""

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_file_path(filename: str) -> str:
    """Returns the absolute path for a compose file in the current test directory"""
    return os.path.join(test_path(), "ipc", filename)


class TestComposeIpc(unittest.TestCase, RunSubprocessMixin):
    def test_ipc_shared_namespace(self) -> None:
        """Create and start two containers with shared ipc namespace"""

        compose_file = compose_file_path("docker-compose-service.yaml")

        try:
            # spin up yaml with two services
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "up",
                "-d",
            ])

            # read ipc namespace from both
            ipc_namespaces = []

            for service in ("ipc_test", "ipc_test0"):
                output, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_file,
                    "exec",
                    service,
                    "readlink",
                    "/proc/self/ns/ipc",
                ])
                ipc_namespaces.append(output)

            # and check that they are equal
            self.assertEqual(ipc_namespaces[0], ipc_namespaces[1])

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
