# SPDX-License-Identifier: GPL-2.0


"""Test how ulimits are applied in podman-compose build."""

import os
import subprocess
import unittest

from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path


def compose_yaml_path():
    """ "Returns the path to the compose file used for this test module"""
    return os.path.join(test_path(), "ulimit_build")


class TestComposeBuildUlimits(unittest.TestCase):
    def test_build_ulimits_ulimit1(self):
        """podman build should receive and apply limits when building service ulimit1"""

        cmd = (
            "coverage",
            "run",
            podman_compose_path(),
            "--verbose",
            "-f",
            os.path.join(compose_yaml_path(), "docker-compose.yaml"),
            "build",
            "--no-cache",
            "ulimit1",
        )
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, check=False, stderr=subprocess.STDOUT, text=True
        )

        self.assertEqual(p.returncode, 0)
        self.assertIn("--ulimit nofile=1001", p.stdout)
        self.assertIn("soft nofile limit: 1001", p.stdout)
        self.assertIn("hard nofile limit: 1001", p.stdout)

    def test_build_ulimits_ulimit2(self):
        """podman build should receive and apply limits when building service ulimit2"""

        cmd = (
            "coverage",
            "run",
            podman_compose_path(),
            "--verbose",
            "-f",
            os.path.join(compose_yaml_path(), "docker-compose.yaml"),
            "build",
            "--no-cache",
            "ulimit2",
        )
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, check=False, stderr=subprocess.STDOUT, text=True
        )

        self.assertEqual(p.returncode, 0)
        self.assertIn("--ulimit nofile=1002", p.stdout)
        self.assertIn("--ulimit nproc=1002:2002", p.stdout)
        self.assertIn("soft process limit: 1002", p.stdout)
        self.assertIn("hard process limit: 2002", p.stdout)
        self.assertIn("soft nofile limit: 1002", p.stdout)
        self.assertIn("hard nofile limit: 1002", p.stdout)

    def test_build_ulimits_ulimit3(self):
        """podman build should receive and apply limits when building service ulimit3"""

        cmd = (
            "coverage",
            "run",
            podman_compose_path(),
            "--verbose",
            "-f",
            os.path.join(compose_yaml_path(), "docker-compose.yaml"),
            "build",
            "--no-cache",
            "ulimit3",
        )
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, check=False, stderr=subprocess.STDOUT, text=True
        )

        self.assertEqual(p.returncode, 0)
        self.assertIn("--ulimit nofile=1003", p.stdout)
        self.assertIn("--ulimit nproc=1003:2003", p.stdout)
        self.assertIn("soft process limit: 1003", p.stdout)
        self.assertIn("hard process limit: 2003", p.stdout)
        self.assertIn("soft nofile limit: 1003", p.stdout)
        self.assertIn("hard nofile limit: 1003", p.stdout)
