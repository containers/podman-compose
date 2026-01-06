# SPDX-License-Identifier: GPL-2.0


"""Test how services can be used in the additional build contexts."""

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    """ "Returns the path to the compose file used for this test module"""
    return os.path.join(test_path(), "additional_contexts_services", "docker-compose.yml")


class TestComposeBuildAdditionalContextsServices(unittest.TestCase, RunSubprocessMixin):
    def test_build_additional_contexts_services(self) -> None:
        # Podman should automatically build the images, resolving the service dependencies.
        # The build will fail if the order is incorrect or something is unresolved.
        self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "build",
        ])
