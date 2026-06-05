# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import tempfile
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "configs"), "docker-compose.yaml")


class TestComposeConfigs(unittest.TestCase, RunSubprocessMixin):
    created_configs = [
        "podman_compose_test_config",
        "podman_compose_test_config_2",
    ]

    def setUp(self) -> None:
        for config in self.created_configs:
            # Once requires-python is >=3.12, delete=False can be changed
            # to delete_on_close=False and the call to os.unlink removed
            with tempfile.NamedTemporaryFile(delete=False) as config_tempfile:
                config_tempfile.write(config.encode('utf-8'))
                config_tempfile.close()
                subprocess.run([
                    "podman",
                    "artifact",
                    "add",
                    "--file-type",
                    "text/plain",
                    config,
                    config_tempfile.name,
                ])
                os.unlink(config_tempfile.name)

    def tearDown(self) -> None:
        for config in self.created_configs:
            self.run_subprocess_assert_returncode([
                "podman",
                "artifact",
                "rm",
                f"{config}",
            ])

    # test if configs are saved and available in respective files of a container
    def test_configs(self) -> None:
        try:
            _, error = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "test",
                ],
                env={
                    "CONFIG_ENV": "config-from-environment",
                    "CONFIG_VAR": "value-from-environment",
                },
            )

            self.assertIn(
                b'WARNING: Service test uses configs.file_config '
                b'(at target /unused_params_warning) with uid, gid, or mode. '
                b'These fields are not supported by this implementation of the Compose file\n',
                error,
            )

            output, _ = self.run_subprocess_assert_returncode(["podman", "logs", "configs_test_1"])
            expected_output = (
                b'/podman_compose_test_config:podman_compose_test_config\n'
                + b'/podman_compose_test_config_2:podman_compose_test_config_2\n'
                + b'/file_config:important-config-is-important\n'
                + b'/etc/custom_location:important-config-is-important\n'
                + b'/unused_params_warning:important-config-is-important\n'
                + b'/content_config:config-from-content\n'
                + b'/content_config_with_var:config-with-value-from-environment\n'
                + b'/environment_config:config-from-environment\n'
            )
            self.assertEqual(
                expected_output.decode(errors='backslashreplace'),
                output.decode(errors='backslashreplace'),
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])

        output, _ = self.run_subprocess_assert_returncode([
            "podman",
            "artifact",
            "ls",
            "--noheading",
            "--format",
            "{{.Repository}}:{{.Tag}}",
        ])
        # assert external artifacts still present; not removed until self.tearDown()
        self.assertIn(b'podman_compose_test_config', output)
        # assert compose-created artifacts correctly removed during podman compose down
        self.assertNotIn(b'localhost/podman-compose/configs_config_', output)
