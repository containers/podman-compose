# SPDX-License-Identifier: GPL-2.0


import os
import unittest

from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestLogs(unittest.TestCase, RunSubprocessMixin):
    @parameterized.expand([
        (
            "all_services_no_flag",
            [],
            [
                b'',
                b'\x1b[1;32m[test1] |\x1b[0m \x1b[37mtest1\x1b[0m',
                b'\x1b[1;33m[test2] |\x1b[0m \x1b[37mtest2\x1b[0m',
                b'\x1b[1;34m[test3] |\x1b[0m \x1b[37mtest3\x1b[0m',
            ],
        ),
        (
            "all_services_flag_no_color",
            ["--no-color"],
            [
                b'',
                b'\x1b[0m[test1] |\x1b[0m test1',
                b'\x1b[0m[test2] |\x1b[0m test2',
                b'\x1b[0m[test3] |\x1b[0m test3',
            ],
        ),
        (
            "all_services_flag_no_log_prefix",
            ["--no-log-prefix"],
            [b'', b'\x1b[37mtest1\x1b[0m', b'\x1b[37mtest2\x1b[0m', b'\x1b[37mtest3\x1b[0m'],
        ),
        (
            "all_services_flag_no_color_no_log_prefix",
            ["--no-color", "--no-log-prefix"],
            [b'', b'test1', b'test2', b'test3'],
        ),
        (
            "one_service_no_flag",
            ["test1"],
            [b'', b'\x1b[1;32m[test1] |\x1b[0m \x1b[37mtest1\x1b[0m'],
        ),
        (
            "one_service_flag_no_color",
            ["test1", "--no-color"],
            [b'', b'\x1b[0m[test1] |\x1b[0m test1'],
        ),
        (
            "one_service_flag_no_log_prefix",
            ["test1", "--no-log-prefix"],
            [b'', b'\x1b[37mtest1\x1b[0m'],
        ),
        (
            "one_service_flag_no_color_no_log_prefix",
            ["test1", "--no-color", "--no-log-prefix"],
            [b'', b'test1'],
        ),
        (
            "two_services_no_flag",
            ["test2", "test3"],
            [
                b'',
                b'\x1b[1;32m[test2] |\x1b[0m \x1b[37mtest2\x1b[0m',
                b'\x1b[1;33m[test3] |\x1b[0m \x1b[37mtest3\x1b[0m',
            ],
        ),
        (
            "two_services_flag_no_color",
            ["test2", "test3", "--no-color"],
            [b'', b'\x1b[0m[test2] |\x1b[0m test2', b'\x1b[0m[test3] |\x1b[0m test3'],
        ),
        (
            "two_services_flag_no_log_prefix",
            ["test2", "test3", "--no-log-prefix"],
            [b'', b'\x1b[37mtest2\x1b[0m', b'\x1b[37mtest3\x1b[0m'],
        ),
        (
            "two_services_flag_no_color_no_log_prefix",
            ["test2", "test3", "--no-color", "--no-log-prefix"],
            [b'', b'test2', b'test3'],
        ),
    ])
    def test_logs(
        self, test_name: str, additional_args: list[str], expected_log: list[bytes]
    ) -> None:
        compose_path = os.path.join(test_path(), "logs/docker-compose.yml")

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "up",
                "-d",
            ])
            command_args = [
                podman_compose_path(),
                "-f",
                compose_path,
                "logs",
            ]
            command_args.extend(additional_args)
            out, _ = self.run_subprocess_assert_returncode(command_args)
            lines = out.split(b'\n')
            lines.sort()
            self.assertEqual(lines, expected_log)
        finally:
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "down",
            ])
