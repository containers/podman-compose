# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(scenario: str) -> str:
    return os.path.join(
        os.path.join(test_path(), "default_net_behavior"), f"docker-compose_{scenario}.yaml"
    )


class TestComposeDefaultNetBehavior(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ('no_nets', 'default_net_behavior_default'),
        ('one_net', 'default_net_behavior_net0'),
        ('two_nets', 'podman'),
        ('with_default', 'default_net_behavior_default'),
        ('no_nets_compat', 'default_net_behavior_default'),
        ('one_net_compat', 'default_net_behavior_default'),
        ('two_nets_compat', 'default_net_behavior_default'),
        ('with_default_compat', 'default_net_behavior_default'),
    ])
    def test_nethost(self, scenario: str, default_net: str) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "up", "-d"],
            )

            container_id_out, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(scenario),
                    "ps",
                    "--format",
                    '{{.ID}}',
                ],
            )
            container_id = container_id_out.decode('utf-8').split('\n')[0]
            output, _ = self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "inspect",
                    container_id,
                    "--format",
                    "{{range $key, $value := .NetworkSettings.Networks }}{{ $key }}\n{{ end }}",
                ],
            )
            self.assertEqual(output.decode('utf-8').strip(), default_net)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "down",
                "-t",
                "0",
            ])
