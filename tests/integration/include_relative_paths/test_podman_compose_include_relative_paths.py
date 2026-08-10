# SPDX-License-Identifier: GPL-2.0

"""
Tests that relative paths (volumes, env_file) inside an included compose
file are resolved against the included file's directory, not the project
root. See https://github.com/containers/podman-compose/issues/1301 and the
Compose Spec include resolution rules.
"""

import os
import textwrap
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_file() -> str:
    return os.path.join(test_path(), "include_relative_paths", "docker-compose.yaml")


class TestIncludeRelativePaths(unittest.TestCase, RunSubprocessMixin):
    def test_relative_paths_in_included_file(self) -> None:
        """
        The included file at ``sub/included.yaml`` references
        ``./local.env``, ``../shared.env``, ``./data:/data:ro`` and
        ``../assets:/assets:ro``. After include resolution these must point
        at paths under ``sub/`` for the ``./`` forms and at the project
        root for the ``../`` forms.
        """
        out, _ = self.run_subprocess_assert_returncode([
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            compose_file(),
            "config",
        ])

        expected = textwrap.dedent("""\
            name: include-relative-paths
            services:
              web:
                env_file:
                - ./sub/./local.env
                - ./sub/../shared.env
                image: nopush/podman-compose-test
                volumes:
                - ./sub/./data:/data:ro
                - ./sub/../assets:/assets:ro

            """)
        self.assertEqual(out.decode("utf-8"), expected)
