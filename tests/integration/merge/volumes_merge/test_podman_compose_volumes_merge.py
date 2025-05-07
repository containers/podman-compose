# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(compose_name):
    """ "Returns the path to the compose file used for this test module"""
    base_path = os.path.join(test_path(), "volumes_merge/")
    return os.path.join(base_path, compose_name)


class TestComposeVolumesMerge(unittest.TestCase, RunSubprocessMixin):
    def test_volumes_merge(self):
        # test if additional compose file overrides host path and access mode of a volume
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose.yaml"),
                "-f",
                compose_yaml_path("docker-compose.override.yaml"),
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "exec",
                "-ti",
                "volumes_merge_web_1",
                "cat",
                "/var/www/html/index.html",
                "/var/www/html/index2.html",
                "/var/www/html/index3.html",
            ])
            self.assertEqual(
                out,
                b"The file from docker-compose.override.yaml\r\n"
                b"The file from docker-compose.override.yaml\r\n"
                b"The file from docker-compose.override.yaml\r\n",
            )

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "volumes_merge_web_1",
            ])
            volumes_info = json.loads(out.decode('utf-8'))[0]
            binds_info = volumes_info["HostConfig"]["Binds"]
            binds_info.sort()

            file_path = os.path.join(test_path(), "volumes_merge/override.txt")
            expected = [
                f'{file_path}:/var/www/html/index.html:ro,rprivate,rbind',
                f'{file_path}:/var/www/html/index2.html:rw,rprivate,rbind',
                f'{file_path}:/var/www/html/index3.html:rw,rprivate,rbind',
            ]
            self.assertEqual(binds_info, expected)
        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose.yaml"),
                "-f",
                compose_yaml_path("docker-compose.override.yaml"),
                "down",
                "-t",
                "0",
            ])
