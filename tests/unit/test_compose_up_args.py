# SPDX-License-Identifier: GPL-2.0

import unittest

from podman_compose import PodmanComposeError
from podman_compose import podman_compose


class TestComposeUpArgs(unittest.TestCase):
    def test_no_attach_can_be_repeated(self) -> None:
        args = podman_compose._parse_args([
            "up",
            "--no-attach",
            "db",
            "--no-attach",
            "cache",
        ])

        self.assertEqual(args.no_attach, ["db", "cache"])

    def test_no_attach_defaults_to_empty_list(self) -> None:
        args = podman_compose._parse_args(["up"])

        self.assertEqual(args.no_attach, [])

    def test_wait_implies_detach(self) -> None:
        args = podman_compose._parse_args(["up", "--wait"])

        self.assertTrue(args.wait)
        self.assertTrue(args.detach)

    def test_wait_allows_explicit_detach(self) -> None:
        args = podman_compose._parse_args(["up", "--detach", "--wait"])

        self.assertTrue(args.detach)

    def test_wait_rejects_attached_exit_options(self) -> None:
        incompatible_options = [
            "--abort-on-container-exit",
            "--abort-on-container-failure",
            "--exit-code-from=app",
        ]

        for option in incompatible_options:
            with self.subTest(option=option):
                with self.assertRaisesRegex(PodmanComposeError, "--wait cannot be combined"):
                    podman_compose._parse_args(["up", "--wait", option])

    def test_wait_error_lists_all_incompatible_options(self) -> None:
        with self.assertRaises(PodmanComposeError) as error:
            podman_compose._parse_args([
                "up",
                "--wait",
                "--abort-on-container-exit",
                "--abort-on-container-failure",
                "--exit-code-from=app",
            ])

        self.assertEqual(
            str(error.exception),
            "--wait cannot be combined with --abort-on-container-exit, "
            "--abort-on-container-failure or --exit-code-from",
        )

    def test_wait_timeout_must_be_non_negative(self) -> None:
        for command in ("up", "start"):
            with self.subTest(command=command):
                with self.assertRaisesRegex(PodmanComposeError, "non-negative integer"):
                    podman_compose._parse_args([command, "--wait-timeout", "-1"])

    def test_zero_wait_timeout_is_allowed(self) -> None:
        args = podman_compose._parse_args(["up", "--wait", "--wait-timeout", "0"])

        self.assertEqual(args.wait_timeout, 0)
