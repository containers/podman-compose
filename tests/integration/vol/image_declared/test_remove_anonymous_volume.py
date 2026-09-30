# SPDX-License-Identifier: GPL-2.0

"""
test_remove_anonymous_volume.py

Tests that `podman compose down --volumes` removes an anonymous volume
declared by a Dockerfile VOLUME instruction.
"""

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    test_dirpath = os.path.dirname(__file__)

    def test_down_with_volumes_removes_anonymous_volume(self) -> None:
        self.addCleanup(
            self.run_subprocess,
            [
                "podman",
                "rmi",
                "--force",
                "--ignore",
                "podman-compose-remove-anonymous-volume-test",
            ],
        )

        try:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                os.path.join(self.test_dirpath, "docker-compose.yaml"),
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "--format",
                '{{range .Mounts}}{{if eq .Destination "/test-volume"}}{{.Name}}{{end}}{{end}}',
                "podman-compose-remove-anonymous-volume-test-container",
            ])
            volume_name = out.decode("utf-8").strip()
            if not volume_name:
                self.fail("Failed to get the name of the anonymous volume")

            # Ensure the volume is removed even if the test fails
            self.addCleanup(self.run_subprocess, ["podman", "volume", "rm", "--force", volume_name])
        finally:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                os.path.join(self.test_dirpath, "docker-compose.yaml"),
                "down",
                "--volumes",
            ])

        self.run_subprocess_assert_returncode(
            ["podman", "volume", "exists", volume_name],
            expected_returncode=1,
        )
