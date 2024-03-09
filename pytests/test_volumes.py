# SPDX-License-Identifier: GPL-2.0
# pylint: disable=redefined-outer-name
import unittest

from podman_compose import parse_short_mount


class ParseShortMountTests(unittest.TestCase):
    def test_multi_propagation(self):
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
