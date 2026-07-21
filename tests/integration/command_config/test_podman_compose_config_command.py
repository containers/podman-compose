# SPDX-License-Identifier: GPL-2.0

import os
import textwrap
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(scenario: str) -> str:
    return os.path.join(
        os.path.join(test_path(), "command_config"), f"docker-compose_{scenario}.yaml"
    )


class TestConfigCommand(unittest.TestCase, RunSubprocessMixin):
    def test_config_quiet(self) -> None:
        """
        Tests podman-compose config command with the --quiet flag.
        """
        config_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            compose_yaml_path("quiet"),
            "config",
            "--quiet",
        ]

        out, _ = self.run_subprocess_assert_returncode(config_cmd)
        self.assertEqual(out.decode("utf-8"), "")

    def test_config_short_syntax_env(self) -> None:
        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path("short_syntax"),
                "config",
            ],
            0,
        )
        expected = textwrap.dedent("""\
            services:
              app:
                command:
                - /bin/busybox
                - sh
                - -c
                - env | grep ZZVAR3
                environment:
                  ZZVAR3: TEST
                image: nopush/podman-compose-test

            """)
        self.assertEqual(out.decode("utf-8"), expected)
