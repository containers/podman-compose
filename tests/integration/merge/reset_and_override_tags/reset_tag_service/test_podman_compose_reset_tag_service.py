# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(
        test_path(), "merge/reset_and_override_tags/reset_tag_service/docker-compose.yaml"
    )


class TestComposeResetTagService(unittest.TestCase, RunSubprocessMixin):
    # test if whole service from docker-compose.yaml file is reset
    def test_reset_tag_service(self) -> None:
        reset_file = os.path.join(
            test_path(),
            "merge/reset_and_override_tags/reset_tag_service/docker-compose.reset_service.yaml",
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

            # app service was fully reset in docker-compose.reset_tag_service.yaml file, therefore
            # does not exist. A new service was created instead.
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "-f",
                reset_file,
                "ps",
            ])
            self.assertNotIn(b"reset_tag_service_app_1", output)
            self.assertIn(b"reset_tag_service_app2_1", output)

            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "-f",
                reset_file,
                "logs",
            ])
            self.assertEqual(output, b"One\n")
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
