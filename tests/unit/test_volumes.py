# SPDX-License-Identifier: GPL-2.0
# pylint: disable=redefined-outer-name
import unittest

from podman_compose import parse_short_mount


class ParseShortMountTests(unittest.TestCase):
    def test_multi_propagation(self) -> None:
        self.assertEqual(
            parse_short_mount("/foo/bar:/baz:U,Z", "/"),
            {
                "type": "bind",
                "source": "/foo/bar",
                "target": "/baz",
                "bind": {
                    "propagation": "U,Z",
                },
            },
        )

    def test_windows_absolute_path(self) -> None:
        # the colon of a drive letter is part of the host path, not a separator
        self.assertEqual(
            parse_short_mount("C:\\data:/data", "/"),
            {
                "type": "bind",
                "source": "C:\\data",
                "target": "/data",
                "bind": {
                    "propagation": "",
                },
            },
        )

    def test_windows_absolute_path_with_option(self) -> None:
        self.assertEqual(
            parse_short_mount("C:\\data:/data:ro", "/"),
            {
                "type": "bind",
                "source": "C:\\data",
                "target": "/data",
                "read_only": True,
                "bind": {
                    "propagation": "",
                },
            },
        )

    def test_windows_absolute_path_forward_slashes(self) -> None:
        mount = parse_short_mount("C:/data:/data", "/")
        self.assertEqual(mount["type"], "bind")
        self.assertEqual(mount["target"], "/data")
        # host path stays absolute with its drive letter, normalization is platform specific
        self.assertTrue(mount["source"].startswith("C:"))

    def test_single_letter_volume_name(self) -> None:
        # a one letter named volume must not be mistaken for a drive letter
        self.assertEqual(
            parse_short_mount("x:/data:ro", "/"),
            {
                "type": "volume",
                "source": "x",
                "target": "/data",
                "read_only": True,
                "bind": {
                    "propagation": "",
                },
            },
        )
