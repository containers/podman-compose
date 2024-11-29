# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "multicompose"), "docker-compose.yml")


class TestComposeMulticompose(unittest.TestCase, RunSubprocessMixin):
    def test_multicompose(self):
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    os.path.join(
                        os.path.join(test_path(), "multicompose"), "d1/docker-compose.yml"
                    ),
                    "-f",
                    os.path.join(
                        os.path.join(test_path(), "multicompose"), "d2/docker-compose.yml"
                    ),
                    "up",
                    "-d",
                ],
            )
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                os.path.join(os.path.join(test_path(), "multicompose"), "d1/docker-compose.yml"),
                "-f",
                os.path.join(os.path.join(test_path(), "multicompose"), "d2/docker-compose.yml"),
                "ps",
            ])
            self.assertIn(b"d1-web1-1", output)
            self.assertIn(b"d1-web2-1", output)

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "exec",
                "-ti",
                "d1-web1-1",
                "sh",
                "-c",
                "set",
            ])
            # checks if `enf_file` was appended, not replaced
            # (which means that we normalize to array before merge)
            self.assertIn(b"var12='d1/12.env'", output)

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "exec",
                "-ti",
                "d1-web2-1",
                "sh",
                "-c",
                "set",
            ])
            # checks if paths inside `d2/docker-compose.yml` directory are relative to `d1`
            self.assertIn(b"var2='d1/2.env'", output)

            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "exec",
                "-ti",
                "d1-web1-1",
                "sh",
                "-c",
                "cat /var/www/html/index.txt",
            ])
            self.assertIn(b"var1=d1/1.env", output)

            # check if project base directory and project name is d1
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "exec",
                "-ti",
                "d1-web2-1",
                "sh",
                "-c",
                "cat /var/www/html/index.txt",
            ])
            self.assertIn(b"var2=d1/2.env", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                os.path.join(os.path.join(test_path(), "multicompose"), "d1/docker-compose.yml"),
                "-f",
                os.path.join(os.path.join(test_path(), "multicompose"), "d2/docker-compose.yml"),
                "down",
                "-t",
                "0",
            ])
