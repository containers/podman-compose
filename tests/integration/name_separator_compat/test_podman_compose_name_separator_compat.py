# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestComposeNameSeparatorCompat(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ('default', { }, '_'),
        ('default', { 'PODMAN_COMPOSE_NAME_SEPARATOR_COMPAT': '1' }, '-'),
        ('compat', { }, '-'),
        ('compat', { 'PODMAN_COMPOSE_NAME_SEPARATOR_COMPAT': '1' }, '-'),
        ('compat', { 'PODMAN_COMPOSE_NAME_SEPARATOR_COMPAT': '0' }, '_'),
    ])
    def test_container_name(self, file: str, env: dict[str, str], expected_sep: str) -> None:
        compose_yaml_path = os.path.join(
            test_path(),
            "name_separator_compat",
            f"docker-compose_{file}.yaml")

        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path, "up", "-d"],
                env=env,
            )

            container_name_out, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path,
                    "ps",
                    "--format",
                    '{{.Names}}',
                ],
                env=env,
            )
            container_name = container_name_out.decode('utf-8').strip()

            expected_container_name = f'name_separator_compat{expected_sep}web{expected_sep}1'

            self.assertEqual(container_name, expected_container_name)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path,
                "down",
                "-t",
                "0",
            ], env=env)
