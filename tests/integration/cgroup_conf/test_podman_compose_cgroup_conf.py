# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    def test_cgroup_conf(self) -> None:
        compose_path = os.path.join(test_path(), "cgroup_conf", "docker-compose.yml")
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
                "cgroup_conf_cgroupconf_1",
            ])

            inspect_out = json.loads(out)
            host_config_map = inspect_out[0].get("HostConfig", {}).get("CgroupConf", {})
            self.assertEqual('712M', host_config_map['memory.high'])
            self.assertEqual('800M', host_config_map['memory.max'])
        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])
