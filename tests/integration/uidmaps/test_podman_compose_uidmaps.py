# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    def test_uidmaps(self):
        compose_path = os.path.join(test_path(), "uidmaps", "docker-compose.yml")
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "uidmaps_touch_1",
            ])

            inspect_out = json.loads(out)
            host_config_map = inspect_out[0].get("HostConfig", {}).get("IDMappings", {})
            self.assertEqual(['0:1:1', '999:0:1'], host_config_map['UidMap'])
            self.assertEqual(['0:1:1', '999:0:1'], host_config_map['GidMap'])
        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])
