# SPDX-License-Identifier: GPL-2.0

import os
import textwrap
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "extends_w_file_nested"), "docker-compose.yml")


class TestComposeExtendsWithFileNested(unittest.TestCase, RunSubprocessMixin):
    def test_extends_w_file_nested(self) -> None:
        out, _ = self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "config",
        ])

        expected = textwrap.dedent("""\
            services:
              web:
                command:
                - /bin/sh
                image: nopush/podman-compose-test
                volumes:
                - /data
                networks:
                  default: null
              important_web:
                command:
                - /bin/sh
                image: nopush/podman-compose-test
                volumes:
                - /data
                - /logs
                networks:
                  default: null
            networks:
              default:
                name: extends_w_file_nested_default

            """)
        self.assertEqual(out.decode("utf-8"), expected)
