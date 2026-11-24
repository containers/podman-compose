# SPDX-License-Identifier: GPL-2.0

import unittest

from podman_compose import PodmanComposeError
from podman_compose import get_no_attach_services
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

    def test_services_are_attached_by_default(self) -> None:
        services = {"web": {}, "db": {"attach": True}, "cache": {"attach": "true"}}

        self.assertEqual(get_no_attach_services(services, []), set())

    def test_attach_false_is_not_attached(self) -> None:
        for value in (False, "false", "False", 0, "0"):
            with self.subTest(value=value):
                services = {"web": {}, "db": {"attach": value}}

                self.assertEqual(get_no_attach_services(services, []), {"db"})

    def test_attach_false_combines_with_no_attach(self) -> None:
        services = {"web": {}, "db": {"attach": False}, "cache": {}}

        self.assertEqual(get_no_attach_services(services, ["cache"]), {"db", "cache"})

    def test_no_attach_overrides_attach_true(self) -> None:
        services = {"web": {"attach": True}}

        self.assertEqual(get_no_attach_services(services, ["web"]), {"web"})

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
