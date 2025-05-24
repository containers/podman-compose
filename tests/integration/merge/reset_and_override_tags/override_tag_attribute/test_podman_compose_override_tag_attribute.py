# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(
        test_path(),
        "merge/reset_and_override_tags/override_tag_attribute/docker-compose.yaml",
    )


class TestComposeOverrideTagAttribute(unittest.TestCase, RunSubprocessMixin):
    # test if a service attribute from docker-compose.yaml file is overridden
    def test_override_tag_attribute(self) -> None:
        override_file = os.path.join(
            test_path(),
            "merge/reset_and_override_tags/override_tag_attribute/docker-compose.override_attribute.yaml",
        )
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "-f",
                override_file,
                "up",
            ])
            # merge rules are still applied
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "-f",
                override_file,
                "logs",
            ])
            self.assertEqual(output, b"One\n")

            # only app service attribute "ports" was overridden
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "override_tag_attribute_app_1",
            ])
            container_info = json.loads(output.decode('utf-8'))[0]
            self.assertEqual(
                container_info['NetworkSettings']["Ports"],
                {"81/tcp": [{"HostIp": "", "HostPort": "8111"}]},
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
