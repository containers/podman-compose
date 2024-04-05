# SPDX-License-Identifier: GPL-2.0


"""Test how secrets in files are passed to podman."""

import os
import subprocess
import unittest

from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path


def compose_yaml_path():
    """ "Returns the path to the compose file used for this test module"""
    return os.path.join(test_path(), "build_secrets")


class TestComposeBuildSecrets(unittest.TestCase):
    def test_run_secret(self):
        """podman run should receive file secrets as --volume

        See build_secrets/docker-compose.yaml for secret names and mount points (aka targets)

        """
        cmd = (
            "coverage",
            "run",
            podman_compose_path(),
            "--dry-run",
            "--verbose",
            "-f",
            os.path.join(compose_yaml_path(), "docker-compose.yaml"),
            "run",
            "test",
        )
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, check=False, stderr=subprocess.STDOUT, text=True
        )
        self.assertEqual(p.returncode, 0)
        secret_path = os.path.join(compose_yaml_path(), "my_secret")
        self.assertIn(f"--volume {secret_path}:/run/secrets/run_secret:ro,rprivate,rbind", p.stdout)
        self.assertIn(f"--volume {secret_path}:/tmp/run_secret2:ro,rprivate,rbind", p.stdout)

    def test_build_secret(self):
        """podman build should receive secrets as --secret, so that they can be used inside the
        Dockerfile in "RUN --mount=type=secret ..." commands.

        """
        cmd = (
            "coverage",
            "run",
            podman_compose_path(),
            "--dry-run",
            "--verbose",
            "-f",
            os.path.join(compose_yaml_path(), "docker-compose.yaml"),
            "build",
        )
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, check=False, stderr=subprocess.STDOUT, text=True
        )
        self.assertEqual(p.returncode, 0)
        secret_path = os.path.join(compose_yaml_path(), "my_secret")
        self.assertIn(f"--secret id=build_secret,src={secret_path}", p.stdout)
        self.assertIn(f"--secret id=build_secret2,src={secret_path}", p.stdout)

    def test_invalid_build_secret(self):
        """build secrets in docker-compose file can only have a target argument without directory
        component

        """
        cmd = (
            "coverage",
            "run",
            podman_compose_path(),
            "--dry-run",
            "--verbose",
            "-f",
            os.path.join(compose_yaml_path(), "docker-compose.yaml.invalid"),
            "build",
        )
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, check=False, stderr=subprocess.STDOUT, text=True
        )
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(
            'ValueError: ERROR: Build secret "build_secret" has invalid target "/build_secret"',
            p.stdout,
        )
