# SPDX-License-Identifier: GPL-2.0


import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestUlimit(unittest.TestCase, RunSubprocessMixin):
    def test_ulimit(self) -> None:
        compose_path = os.path.join(test_path(), "ulimit/docker-compose.yaml")
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "logs",
                "ulimit_ulimit1_1",
            ])
            split_output = out.strip(b"\n").split(b"\n")

            # trow away system specific default ulimit values
            output_part = [
                el
                for el in split_output
                if not el.startswith(b"soft process") and not el.startswith(b"hard process")
            ]
            self.assertEqual(
                output_part,
                [
                    b"soft nofile limit 1001",
                    b"hard nofile limit 1001",
                ],
            )

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "logs",
                "ulimit_ulimit2_1",
            ])
            self.assertEqual(
                out,
                b"soft process limit 1002\nhard process limit 2002\nsoft nofile limit 1002\n"
                b"hard nofile limit 1002\n",
            )

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "logs",
                "ulimit_ulimit3_1",
            ])
            self.assertEqual(
                out,
                b"soft process limit 1003\nhard process limit 2003\nsoft nofile limit 1003\n"
                b"hard nofile limit 1003\n",
            )
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])
