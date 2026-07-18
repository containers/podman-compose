# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import unittest
from typing import Any

from parameterized import parameterized

from podman_compose import flat_deps
from podman_compose import rec_merge
from podman_compose import resolve_extends


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

    def test_extends_services_with_dependents(self) -> None:
        services: dict[str, dict[str, Any]] = {
            "base": {"image": "base"},
            "child": {"extends": {"service": "base"}, "command": ["run"]},
            "base_consumer": {
                "depends_on": {"base": {"condition": "service_started"}},
            },
            "child_consumer": {
                "depends_on": {"child": {"condition": "service_started"}},
            },
        }

        flat_deps(services, with_extends=True)
        service_names = sorted((len(service["_deps"]), name) for name, service in services.items())
        resolve_extends(services, [name for _, name in service_names], {})

        self.assertEqual(services["child"]["image"], "base")
        self.assertEqual(services["child"]["command"], ["run"])
        self.assertEqual(
            {dependency.name for dependency in services["child"]["_dependents"]},
            {"child_consumer"},
        )
