# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    return os.path.join(
        test_path(),
        "merge/reset_and_override_tags/reset_tag_attribute/docker-compose.yaml",
    )


class TestComposeResetTagAttribute(unittest.TestCase, RunSubprocessMixin):
    # test if the attribute of the service is correctly reset
    def test_reset_tag_attribute(self):
        reset_file = os.path.join(
            test_path(),
            "merge/reset_and_override_tags/reset_tag_attribute/docker-compose.reset_attribute.yaml",
        )
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "-f",
                reset_file,
                "up",
            ])

            # the service still exists, but its command attribute was reset in
            # docker-compose.reset_tag_attribute.yaml file and is now empty
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "-f",
                reset_file,
                "ps",
            ])
            self.assertIn(b"reset_tag_attribute_app_1", output)

            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "-f",
                reset_file,
                "logs",
            ])
            self.assertEqual(output, b"")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
