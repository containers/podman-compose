# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path():
    return os.path.join(os.path.join(test_path(), "seccomp"), "docker-compose.yml")


class TestComposeSeccomp(unittest.TestCase, RunSubprocessMixin):
    @unittest.skip(
        "Skip till security_opt seccomp from 'docker-compose.yml' will be able to accept a "
        "relative path of 'default.json' file. Now test works as expected but only with the "
        "absolute path."
    )
    # test if seccomp uses custom seccomp profile file 'default.json' where command mkdir is not
    # allowed
    def test_seccomp(self):
        try:
            output, _, return_code = self.run_subprocess(
                [podman_compose_path(), "-f", compose_yaml_path(), "run", "--rm", "web1"],
            )
            self.assertEqual(return_code, 1)
            self.assertIn(
                b"mkdir: can't create directory '/tmp_test': Operation not permitted", output
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
