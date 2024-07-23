# SPDX-License-Identifier: GPL-2.0
import unittest

from parameterized import parameterized

from podman_compose import normalize_service


class TestNormalizeService(unittest.TestCase):
    @parameterized.expand([
        ({"test": "test"}, {"test": "test"}),
        ({"build": "."}, {"build": {"context": "."}}),
        ({"build": "./dir-1"}, {"build": {"context": "./dir-1"}}),
        ({"build": {"context": "./dir-1"}}, {"build": {"context": "./dir-1"}}),
        (
            {"build": {"dockerfile": "dockerfile-1"}},
            {"build": {"dockerfile": "dockerfile-1"}},
        ),
        (
            {"build": {"context": "./dir-1", "dockerfile": "dockerfile-1"}},
            {"build": {"context": "./dir-1", "dockerfile": "dockerfile-1"}},
        ),
        (
            {"build": {"additional_contexts": ["ctx=../ctx", "ctx2=../ctx2"]}},
            {"build": {"additional_contexts": ["ctx=../ctx", "ctx2=../ctx2"]}},
        ),
        (
            {"build": {"additional_contexts": {"ctx": "../ctx", "ctx2": "../ctx2"}}},
            {"build": {"additional_contexts": ["ctx=../ctx", "ctx2=../ctx2"]}},
        ),
    ])
    def test_simple(self, input, expected):
        self.assertEqual(normalize_service(input), expected)

    @parameterized.expand([
        ({"test": "test"}, {"test": "test"}),
        ({"build": "."}, {"build": {"context": "./sub_dir/."}}),
        ({"build": "./dir-1"}, {"build": {"context": "./sub_dir/dir-1"}}),
        ({"build": {"context": "./dir-1"}}, {"build": {"context": "./sub_dir/dir-1"}}),
        (
            {"build": {"dockerfile": "dockerfile-1"}},
            {"build": {"context": "./sub_dir", "dockerfile": "dockerfile-1"}},
        ),
        (
            {"build": {"context": "./dir-1", "dockerfile": "dockerfile-1"}},
            {"build": {"context": "./sub_dir/dir-1", "dockerfile": "dockerfile-1"}},
        ),
    ])
    def test_normalize_service_with_sub_dir(self, input, expected):
        self.assertEqual(normalize_service(input, sub_dir="./sub_dir"), expected)

    @parameterized.expand([
        ([], []),
        (["sh"], ["sh"]),
        (["sh", "-c", "date"], ["sh", "-c", "date"]),
        ("sh", ["sh"]),
        ("sleep infinity", ["sleep", "infinity"]),
        (
            "bash -c 'sleep infinity'",
            ["bash", "-c", "sleep infinity"],
        ),
    ])
    def test_command_like(self, input, expected):
        for key in ['command', 'entrypoint']:
            input_service = {}
            input_service[key] = input

            expected_service = {}
            expected_service[key] = expected
            self.assertEqual(normalize_service(input_service), expected_service)
