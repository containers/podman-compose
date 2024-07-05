# SPDX-License-Identifier: GPL-2.0


import os
import unittest

from parameterized import parameterized

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


class TestLifetime(unittest.TestCase, RunSubprocessMixin):
    def test_up_single_container(self):
        """Podman compose up should be able to start containers one after another"""

        compose_path = os.path.join(test_path(), "lifetime/up_single_container/docker-compose.yml")

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
                "container1",
            ])

            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
                "container2",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
                "container1",
            ])

            self.assertEqual(out, b"test1\n")

            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
                "container2",
            ])

            self.assertEqual(out, b"test2\n")

        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])

    @parameterized.expand([
        ("no_ports", "up_single_container_many_times"),
        ("with_ports", "up_single_container_many_times_with_ports"),
    ])
    def test_up_single_container_many_times(self, name, subdir):
        """Podman compose up should be able to start a container many times after it finishes
        running.
        """

        compose_path = os.path.join(test_path(), f"lifetime/{subdir}/docker-compose.yml")

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
                "container1",
            ])

            for _ in range(0, 3):
                self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_path,
                    "up",
                    "-d",
                    "container2",
                ])

            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
                "container1",
            ])

            self.assertEqual(out, b"test1\n")

            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
                "container2",
            ])

            # BUG: container should be started 3 times, not 4.
            self.assertEqual(out, b"test2\n" * 4)

        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])
