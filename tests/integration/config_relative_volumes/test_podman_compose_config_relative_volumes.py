# SPDX-License-Identifier: GPL-2.0

import os
import textwrap
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.dirname(__file__), "docker-compose.yml")


class TestConfigRelativeVolumes(unittest.TestCase, RunSubprocessMixin):
    def test_config_expands_relative_paths_to_absolute(self) -> None:
        out, _ = self.run_subprocess_assert_returncode([
            "python3",
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "config",
        ])

        base_dir = os.path.dirname(compose_yaml_path())
        expected_data = os.path.abspath(os.path.join(base_dir, "data"))
        expected_outside = os.path.abspath(os.path.join(base_dir, "..", "outside"))

        expected = textwrap.dedent(f"""\
            services:
              test:
                command: sleep infinity
                image: nopush/podman-compose-test
                volumes:
                - {expected_data}:/container/data:ro
                - {expected_outside}:/container/outside

            """)
        self.assertEqual(out.decode("utf-8"), expected)
