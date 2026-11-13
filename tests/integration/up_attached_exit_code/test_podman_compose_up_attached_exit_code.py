# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(name: str = "docker-compose.yml") -> str:
    return os.path.join(test_path(), "up_attached_exit_code", name)


class TestUpAttachedExitCode(unittest.TestCase, RunSubprocessMixin):
    def test_attached_up_returns_nonzero_on_create_failure(self) -> None:
        try:
            # The image is valid but the device does not exist, so `podman create`
            # fails. The exit code must be propagated. The timeout guards against a
            # regression where attached `up` hangs instead of returning.
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(), "up"],
                125,
                timeout=10,
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_attached_up_returns_zero_on_success(self) -> None:
        try:
            # A container that starts and exits 0 must not change the exit code.
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path("docker-compose-success.yml"),
                    "up",
                ],
                0,
                timeout=10,
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose-success.yml"),
                "down",
            ])

    def test_attached_up_failure_takes_precedence_over_exit_code_from(self) -> None:
        try:
            # An attached up failure must win over --exit-code-from: `up` returns the
            # create error (125) instead of the exit code of the service named
            # by --exit-code-from (42)
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path("docker-compose-exit-code-from.yml"),
                    "up",
                    "--exit-code-from=exit_code",
                ],
                125,
                timeout=10,
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path("docker-compose-exit-code-from.yml"),
                "down",
            ])
