# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access

import unittest
from typing import Any

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
        (
            "service environment with unpopulated ${VARIABLE:-default} format",
            {"environment": {"v100": "${v100:-low priority}", "actual-v100": "$v100"}},
            {"environment": {"v100": "low priority", "actual-v100": "low priority"}},
        ),
        (
            "service environment with populated ${VARIABLE:-default} format",
            {"environment": {"v1": "${v1:-low priority}", "actual-v1": "$v1"}},
            {"environment": {"v1": "high priority", "actual-v1": "high priority"}},
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
    def test_rec_subs(self, desc: str, input: Any, expected: Any) -> None:
        sub_dict = {"v1": "high priority", "empty": ""}
        result = rec_subs(input, sub_dict)
        self.assertEqual(result, expected, msg=desc)

    def test_env_var_substitution_in_dictionary_keys(self) -> None:
        sub_dict = {"NAME": "TEST1", "NAME2": "TEST2"}
        input = {
            'services': {
                'test': {
                    'image': 'busybox',
                    'labels': {
                        '$NAME and ${NAME2}': '${NAME2} and $NAME',
                        'test1.${NAME}': 'test1',
                        '$NAME': '${NAME2}',
                        '${NAME}.test2': 'Host(`${NAME2}`)',
                    },
                }
            }
        }
        result = rec_subs(input, sub_dict)
        expected = {
            'services': {
                'test': {
                    'image': 'busybox',
                    'labels': {
                        'TEST1 and TEST2': 'TEST2 and TEST1',
                        'test1.TEST1': 'test1',
                        'TEST1': 'TEST2',
                        'TEST1.test2': 'Host(`TEST2`)',
                    },
                }
            }
        }
        self.assertEqual(result, expected)
