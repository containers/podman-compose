# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import unittest
from typing import Any

from parameterized import parameterized

from podman_compose import rec_merge


class TestRecMergeHealthcheck(unittest.TestCase):
    """healthcheck.test is replaced by later files, like command and entrypoint."""

    @parameterized.expand([
        (
            "list_replaces_list",
            {"healthcheck": {"test": ["CMD", "a"], "interval": "10s"}},
            {"healthcheck": {"test": ["CMD", "b"]}},
            {"healthcheck": {"test": ["CMD", "b"], "interval": "10s"}},
        ),
        (
            "string_replaces_list",
            {"healthcheck": {"test": ["CMD", "a"]}},
            {"healthcheck": {"test": "curl -f http://localhost"}},
            {"healthcheck": {"test": "curl -f http://localhost"}},
        ),
        (
            "list_replaces_string",
            {"healthcheck": {"test": "curl -f http://localhost"}},
            {"healthcheck": {"test": ["CMD-SHELL", "exit 0"]}},
            {"healthcheck": {"test": ["CMD-SHELL", "exit 0"]}},
        ),
        (
            "other_keys_still_merge",
            {"healthcheck": {"test": ["CMD", "a"], "interval": "10s"}},
            {"healthcheck": {"retries": 3}},
            {"healthcheck": {"test": ["CMD", "a"], "interval": "10s", "retries": 3}},
        ),
    ])
    def test_healthcheck_test_is_replaced(
        self,
        _: str,
        target: dict[str, Any],
        source: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        self.assertEqual(rec_merge(target, source), expected)
