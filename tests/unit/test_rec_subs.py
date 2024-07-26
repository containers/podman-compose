# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access

import unittest

from parameterized import parameterized

from podman_compose import rec_subs


class TestRecSubs(unittest.TestCase):
    substitutions = [
        # dict with environment variables
        (
            "service's environment is low priority",
            {"environment": {"v1": "low priority", "actual-v1": "$v1"}},
            {"environment": {"v1": "low priority", "actual-v1": "high priority"}},
        ),
        (
            "service's environment can be used in other values",
            {"environment": {"v100": "v1.0.0", "image": "abc:$v100"}},
            {"environment": {"v100": "v1.0.0", "image": "abc:v1.0.0"}},
        ),
        (
            "Non-variable should not be substituted",
            {"environment": {"non_var": "$$v1", "vx": "$non_var"}, "image": "abc:$non_var"},
            {"environment": {"non_var": "$v1", "vx": "$v1"}, "image": "abc:$v1"},
        ),
        # list
        (
            "Values in list are substituted",
            ["$v1", "low priority"],
            ["high priority", "low priority"],
        ),
        # str
        (
            "Value with ${VARIABLE} format",
            "${v1}",
            "high priority",
        ),
        (
            "Value with ${VARIABLE:-default} format",
            ["${v1:-default}", "${empty:-default}", "${not_exits:-default}"],
            ["high priority", "default", "default"],
        ),
        (
            "Value with ${VARIABLE-default} format",
            ["${v1-default}", "${empty-default}", "${not_exits-default}"],
            ["high priority", "", "default"],
        ),
        (
            "Value $$ means $",
            "$$v1",
            "$v1",
        ),
    ]

    @parameterized.expand(substitutions)
    def test_rec_subs(self, desc, input, expected):
        sub_dict = {"v1": "high priority", "empty": ""}
        result = rec_subs(input, sub_dict)
        self.assertEqual(result, expected, msg=desc)
