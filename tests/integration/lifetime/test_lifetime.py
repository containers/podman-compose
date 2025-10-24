# SPDX-License-Identifier: GPL-2.0


import os
import time
import unittest

from packaging import version
from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestLifetime(unittest.TestCase, RunSubprocessMixin):
    def test_up_single_container(self) -> None:
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
                "--no-log-prefix",
                "--no-color",
                "container1",
            ])

            self.assertEqual(out, b"test1\n")

            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
                "--no-log-prefix",
                "--no-color",
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
    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_up_single_container_many_times(self, name: str, subdir: str) -> None:
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
                "--no-log-prefix",
                "--no-color",
                "container1",
            ])

            self.assertEqual(out, b"test1\n")

            # "restart: always" keeps restarting container until its removal
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
                "--no-log-prefix",
                "--no-color",
                "container2",
            ])

            if not out.startswith(b"test2\ntest2"):
                time.sleep(1)
                out, _ = self.run_subprocess_assert_returncode([
                    podman_compose_path(),
                    "-f",
                    compose_path,
                    "logs",
                    "--no-log-prefix",
                    "--no-color",
                    "container2",
                ])
            self.assertTrue(out.startswith(b"test2\ntest2"))
        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
                "-t",
                "0",
            ])
