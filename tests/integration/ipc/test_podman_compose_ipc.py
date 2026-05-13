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


def podman_compose_simulate(
    compose_command: str, compose_file: str, service: str | None
) -> subprocess.CompletedProcess:
    """Helper function, uses --dry-run to simulate a run of podman compose <command>"""

    return podman_compose_invoke(
        compose_command, compose_file, service, compose_options=("--dry-run", "--verbose")
    )


class TestComposeIpc(unittest.TestCase):
    def test_no_ipc(self) -> None:
        """Do not pass --ipc if there is no ipc element in the config"""
        p = podman_compose_simulate("run", "docker-compose-no-ipc.yaml", "ipc_test")
        self.assertNotIn("--ipc", p.stdout)
        self.assertNotIn("Error", p.stdout)
        self.assertEqual(p.returncode, 0)

    def test_pass_no_ipc_to_build(self) -> None:
        """Do not pass --ipc to podman build"""
        p = podman_compose_simulate("build", "docker-compose-host.yaml", "ipc_test")
        self.assertNotIn("--ipc", p.stdout)
        self.assertNotIn("Error", p.stdout)
        self.assertEqual(p.returncode, 0)

    def test_invalid_ipc(self) -> None:
        """Throw ValueError on invalid ipc mode"""
        p = podman_compose_simulate("run", "docker-compose-invalid.yaml", "ipc_test")
        self.assertIn("ValueError: invalid ipc mode [invalid]", p.stdout)
        self.assertNotEqual(p.returncode, 0)

    def test_invalid_service_name(self) -> None:
        """Throw ValueError if ipc: "service:<name>" refers to an invalid service name"""
        p = podman_compose_simulate("run", "docker-compose-invalid-service.yaml", "ipc_test")
        self.assertIn(
            "ValueError: invalid ipc mode [service:invalid], service [invalid] does not exist",
            p.stdout,
        )
        self.assertNotEqual(p.returncode, 0)

    def test_pass_ipc(self) -> None:
        """Pass correct --ipc parameter to podman run"""

        test_cases = (
            ("docker-compose-emptystring.yaml", ""),
            ("docker-compose-container.yaml", "container:ipc_test0_container"),
            ("docker-compose-host.yaml", "host"),
            ("docker-compose-none.yaml", "none"),
            ("docker-compose-ns.yaml", "ns:namespace_id"),
            ("docker-compose-private.yaml", "private"),
            ("docker-compose-shareable.yaml", "shareable"),
            ("docker-compose-service.yaml", "container:ipc_test0_container"),
        )

        for compose_file, ipc_mode in test_cases:
            for compose_command in ("run", "up"):
                p = podman_compose_simulate(compose_command, compose_file, "ipc_test")
                self.assertIn(f"--ipc {ipc_mode} ", p.stdout)
                self.assertNotIn("Error", p.stdout)
                self.assertEqual(p.returncode, 0)

    def test_up_empty_string(self) -> None:
        """Create and start container with ipc mode "" (empty string)"""

        compose_file = "docker-compose-emptystring.yaml"

        p = podman_compose_invoke("up", compose_file)
        podman_compose_invoke("down", compose_file)

        self.assertNotIn("Error", p.stdout)
        self.assertEqual(p.returncode, 0)

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
