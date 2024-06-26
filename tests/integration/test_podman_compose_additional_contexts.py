# SPDX-License-Identifier: GPL-2.0


"""Test how additional contexts are passed to podman."""

import os
import subprocess
import unittest

from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path


def compose_yaml_path():
    """ "Returns the path to the compose file used for this test module"""
    return os.path.join(test_path(), "additional_contexts", "project")


class TestComposeBuildAdditionalContexts(unittest.TestCase):
    def test_build_additional_context(self):
        """podman build should receive additional contexts as --build-context

        See additional_context/project/docker-compose.yaml for context paths
        """
        cmd = (
            "coverage",
            "run",
            podman_compose_path(),
            "--dry-run",
            "--verbose",
            "-f",
            os.path.join(compose_yaml_path(), "docker-compose.yml"),
            "build",
        )
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            check=False,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.assertEqual(p.returncode, 0)
        self.assertIn("--build-context=data=../data_for_dict", p.stdout)
        self.assertIn("--build-context=data=../data_for_list", p.stdout)
