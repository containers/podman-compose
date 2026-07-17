# SPDX-License-Identifier: GPL-2.0

import unittest

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
