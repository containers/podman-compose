# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""

# pylint: disable=redefined-outer-name
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    def test_with_docker_sock(self) -> None:
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "docker_sock", "docker-compose.yaml"),
            "up",
            "-d",
        ]

        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "docker_sock", "docker-compose.yaml"),
            "down",
            "--volumes",
        ]

        try:
            self.run_subprocess_assert_returncode(up_cmd)

        finally:
            out, _, return_code = self.run_subprocess(down_cmd)
            self.assertEqual(return_code, 0)
