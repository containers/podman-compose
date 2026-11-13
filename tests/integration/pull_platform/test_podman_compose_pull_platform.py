# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    base_path = os.path.join(test_path(), "pull_platform")
    return os.path.join(base_path, "docker-compose.yml")


class TestComposePullPlatform(unittest.TestCase, RunSubprocessMixin):
    def test_pull_with_platform(self) -> None:
        _, error = self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "--verbose",
            "-f",
            compose_yaml_path(),
            "pull",
        ])

        # A plain exit-code check would not catch a regression: on a host whose
        # architecture matches the declared platform, pulling without `--platform`
        # also succeeds.
        self.assertIn(
            b"podman pull --platform linux/amd64 docker.io/library/alpine:latest",
            error,
        )
