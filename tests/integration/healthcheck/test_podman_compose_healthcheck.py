# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from packaging import version

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


@unittest.skipIf(
    get_podman_version() < version.parse("4.6.0"),
    "--health-startup-interval flag is not supported below 4.6.0.",
)
class TestHealthcheck(unittest.TestCase, RunSubprocessMixin):
    def test_healthcheck(self) -> None:
        compose_path = os.path.join(os.path.join(test_path(), "healthcheck"), "docker-compose.yml")

        try:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "ps",
                "-a",
                "--filter",
                "label=io.podman.compose.project=healthcheck",
                "--format",
                '"{{.ID}}"',
            ])
            self.assertNotEqual(out, b"")

            container_id = out.decode("utf-8").strip().replace('"', "")
            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "inspect",
                container_id,
            ])
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

        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])
