# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def bad_compose_yaml_path() -> str:
    base_path = os.path.join(test_path(), "parse-error")
    return os.path.join(base_path, "docker-compose-error.yml")


def good_compose_yaml_path() -> str:
    base_path = os.path.join(test_path(), "parse-error")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposeBuildParseError(unittest.TestCase, RunSubprocessMixin):
    def test_no_error(self) -> None:
        try:
            _, err = self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", good_compose_yaml_path(), "config"], 0
            )
            self.assertEqual(b"", err)

        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-f",
                bad_compose_yaml_path(),
                "down",
            ])

    def test_simple_parse_error(self) -> None:
        try:
            _, err = self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", bad_compose_yaml_path(), "config"], 1
            )
            self.assertIn(b"could not find expected ':'", err)
            self.assertNotIn(b"\nTraceback (most recent call last):\n", err)

        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-f",
                bad_compose_yaml_path(),
                "down",
            ])

    def test_verbose_parse_error_contains_stack_trace(self) -> None:
        try:
            _, err = self.run_subprocess_assert_returncode(
                [podman_compose_path(), "--verbose", "-f", bad_compose_yaml_path(), "config"], 1
            )
            self.assertIn(b"\nTraceback (most recent call last):\n", err)

        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-f",
                bad_compose_yaml_path(),
                "down",
            ])
