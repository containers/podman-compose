# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(suffix: str = "") -> str:
    return os.path.join(os.path.join(test_path(), "include"), f"docker-compose{suffix}.yaml")


class TestPodmanComposeInclude(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ("string", ""),
        ("dict", "_include_dict"),
    ])
    def test_podman_compose_include(self, name: str, compose_suffix: str) -> None:
        try:
            self.run_subprocess_assert_returncode([
                "coverage",
                "run",
                podman_compose_path(),
                "-f",
                compose_yaml_path(f"{compose_suffix}"),
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "ps",
                "-a",
                "--filter",
                "label=io.podman.compose.project=include",
                "--format",
                '"{{.Names}}"',
            ])
            # two services from included compose files were created
            self.assertEqual(out, b'"include_web_1"\n"include_web2_1"\n')
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
