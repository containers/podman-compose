# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(failure_order: str) -> str:
    return os.path.join(test_path(), "abort", f"docker-compose-fail-{failure_order}.yaml")


class TestComposeAbort(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        ("exit", "first", 0),
        ("failure", "first", 1),
        ("exit", "second", 0),
        ("failure", "second", 1),
        ("exit", "simultaneous", 0),
        ("failure", "simultaneous", 1),
        ("exit", "none", 0),
        ("failure", "none", 0),
    ])
    def test_abort(self, abort_type: str, failure_order: str, expected_exit_code: int) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(failure_order),
                    "up",
                    f"--abort-on-container-{abort_type}",
                ],
                expected_exit_code,
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(failure_order),
                "down",
            ])
