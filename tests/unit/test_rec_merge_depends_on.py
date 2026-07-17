# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import unittest
from typing import Any

from parameterized import parameterized

from podman_compose import rec_merge


class TestRecMergeDependsOn(unittest.TestCase):
    """Test rec_merge with mixed list/dict depends_on."""

    @parameterized.expand([
        (
            "dict_target_list_source",
            {"depends_on": {"db": {"condition": "service_healthy"}}},
            {"depends_on": ["redis"]},
            {
                "depends_on": {
                    "db": {"condition": "service_healthy"},
                    "redis": {},
                },
            },
        ),
        (
            "list_target_dict_source",
            {"depends_on": ["db", "redis"]},
            {"depends_on": {"cache": {"condition": "service_started"}}},
            {
                "depends_on": {
                    "db": {},
                    "redis": {},
                    "cache": {"condition": "service_started"},
                },
            },
        ),
        (
            "dict_target_list_source_overlapping_keys",
            {"depends_on": {"db": {"condition": "service_healthy"}}},
            {"depends_on": ["db", "redis"]},
            {
                "depends_on": {
                    "db": {"condition": "service_healthy"},
                    "redis": {},
                },
            },
        ),
        (
            "list_target_dict_source_overlapping_keys",
            {"depends_on": ["db", "redis"]},
            {"depends_on": {"db": {"condition": "service_healthy"}}},
            {
                "depends_on": {
                    "db": {"condition": "service_healthy"},
                    "redis": {},
                },
            },
        ),
    ])
    def test_rec_merge_depends_on(
        self,
        name: str,
        target: dict[str, Any],
        source: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        result = rec_merge(target, source)
        self.assertEqual(result, expected)

    def test_three_way_mixed_depends_on(self) -> None:
        from_service: dict[str, Any] = {
            "image": "myimage:latest",
            "depends_on": {"db": {"condition": "service_healthy"}},
        }
        service: dict[str, Any] = {
            "depends_on": ["db", "redis"],
            "environment": {"FOO": "bar"},
        }
        result = rec_merge({}, from_service, service)
        self.assertEqual(
            result,
            {
                "image": "myimage:latest",
                "depends_on": {
                    "db": {"condition": "service_healthy"},
                    "redis": {},
                },
                "environment": {"FOO": "bar"},
            },
        )
