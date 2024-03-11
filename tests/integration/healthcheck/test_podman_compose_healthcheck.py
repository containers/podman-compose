# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "healthcheck"), "docker-compose.yml")


class TestHealthecheck(unittest.TestCase, RunSubprocessMixin):
    def test_healthcheck(self) -> None:
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "healthcheck", "docker-compose.yml"),
            "up",
            "-d",
        ]
        self.run_subprocess_assert_returncode(up_cmd)

        command_container_id = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=healthcheck",
            "--format",
            '"{{.ID}}"',
        ]
        out, _ = self.run_subprocess_assert_returncode(command_container_id)
        self.assertNotEqual(out, b"")
        container_id = out.decode("utf-8").strip().replace('"', "")

        command_inspect = ["podman", "container", "inspect", container_id]

        out, _ = self.run_subprocess_assert_returncode(command_inspect)
        out_string = out.decode("utf-8")
        inspect = json.loads(out_string)
        healthcheck_obj = inspect[0]["Config"]["Healthcheck"]
        expected = {
            "Test": ["CMD-SHELL", "curl -f http://localhost || exit 1"],
            "StartPeriod": 10000000000,
            "Interval": 60000000000,
            "Timeout": 10000000000,
            "Retries": 3,
        }
        self.assertEqual(healthcheck_obj, expected)

        # StartInterval is not available in the config object
        create_obj = inspect[0]["Config"]["CreateCommand"]
        self.assertIn("--health-startup-interval", create_obj)
