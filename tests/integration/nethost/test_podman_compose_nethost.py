# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "nethost"), "docker-compose.yaml")


class TestComposeNethost(unittest.TestCase, RunSubprocessMixin):
    # check that the container is placed in the host network namespace
    def test_nethost(self) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(), "up", "-d"],
            )

            container_id_out, _ = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "ps",
                    "--format",
                    '{{.ID}}',
                ],
            )
            container_id = container_id_out.decode('utf-8').split('\n')[0]

            output, _ = self.run_subprocess_assert_returncode(
                [
                    "podman",
                    "inspect",
                    "--format",
                    "{{.HostConfig.NetworkMode}}",
                    container_id,
                ],
            )
            self.assertEqual(output.decode().strip(), "host")

            host_netns, _ = self.run_subprocess_assert_returncode(
                ["readlink", "/proc/self/ns/net"],
            )
            container_netns, _ = self.run_subprocess_assert_returncode(
                ["podman", "exec", container_id, "readlink", "/proc/self/ns/net"],
            )
            self.assertEqual(container_netns.decode().strip(), host_netns.decode().strip())
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
