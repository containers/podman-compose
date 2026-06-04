# SPDX-License-Identifier: GPL-2.0

"""Test passing of ipc mode to podman."""

from __future__ import annotations

import os
import re
import subprocess
import unittest

from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_file_path(filename: str) -> str:
    """Returns the absolute path for a compose file in the current test directory"""
    return os.path.join(test_path(), "ipc", filename)


def podman_compose_invoke(
    compose_command: str, compose_file: str, service: str | None = None, compose_options: tuple = ()
) -> subprocess.CompletedProcess:
    """Helper function, execute a run of podman compose <command>"""
    cmd = (
        ("coverage", "run", podman_compose_path())
        + compose_options
        + ("-f", compose_file_path(compose_file), compose_command)
    )

    if service:
        cmd += (service,)

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        check=False,
        stderr=subprocess.STDOUT,
        text=True,
    )


class TestComposeIpc(unittest.TestCase):
    def test_up_shared_namespace(self) -> None:
        """Create and start two containers with shared ipc namespace"""

        compose_file = "docker-compose-service.yaml"

        p = podman_compose_invoke("up", compose_file)
        podman_compose_invoke("down", compose_file)

        # check that both /proc/self/ns/ipc point to the same target
        matches = re.findall(r'/proc/\d+/ns/ipc:.+', p.stdout)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0], matches[1])
        self.assertNotIn("Error", p.stdout)
        self.assertEqual(p.returncode, 0)
