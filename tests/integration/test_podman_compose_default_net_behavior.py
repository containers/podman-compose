# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path(scenario):
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
    def test_nethost(self, scenario, default_net):
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(scenario), "up", "-d"],
            )

            container_id, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(scenario),
                    "ps",
                    "--format",
                    '{{.ID}}',
                ],
            )
            container_id = container_id.decode('utf-8').split('\n')[0]
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
