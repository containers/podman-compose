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
        "merge/reset_and_override_tags/override_tag_environment/docker-compose.yaml",
    )


class TestComposeOverrideTagEnvironment(unittest.TestCase, RunSubprocessMixin):
    # test if the environment attribute of a service from docker-compose.yaml is overridden
    def test_override_tag_environment(self) -> None:
        override_file = os.path.join(
            test_path(),
            "merge/reset_and_override_tags/override_tag_environment/docker-compose.override_environment.yaml",
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

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "override_tag_environment_app_1",
            ])
            container_info = json.loads(output.decode("utf-8"))[0]
            env_list = container_info["Config"]["Env"]

            self.assertIn("VAR_A=overridden_a", env_list)
            # VAR_B was in base compose file but must not be present when environment is overridden
            self.assertNotIn("VAR_B=initial_b", env_list)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
