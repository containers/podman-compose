from __future__ import annotations

import copy
import unittest
from typing import Any

from parameterized import parameterized

from podman_compose import OverrideTag
from podman_compose import ResetTag
from podman_compose import normalize_service


class TestNormalizeServicesSimple(unittest.TestCase):
    @parameterized.expand([
        (
            {"depends_on": "my_service"},
            {"depends_on": {"my_service": {"condition": "service_started"}}},
        ),
        (
            {"depends_on": ["my_service"]},
            {"depends_on": {"my_service": {"condition": "service_started"}}},
        ),
        (
            {"depends_on": ["my_service1", "my_service2"]},
            {
                "depends_on": {
                    "my_service1": {"condition": "service_started"},
                    "my_service2": {"condition": "service_started"},
                },
            },
        ),
        (
            {"depends_on": {"my_service": {"condition": "service_started"}}},
            {"depends_on": {"my_service": {"condition": "service_started"}}},
        ),
        (
            {"depends_on": {"my_service": {"condition": "service_healthy"}}},
            {"depends_on": {"my_service": {"condition": "service_healthy"}}},
        ),
    ])
    def test_normalize_service_simple(
        self, test_case: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        copy.deepcopy(test_case)
        result = normalize_service(test_case)
        self.assertEqual(result, expected)

    def test_normalize_service_entry_tags(self) -> None:
        result = normalize_service({
            "depends_on": {
                "a": OverrideTag({"condition": "service_healthy"}),
                "b": ResetTag(),
                "c": {},
            }
        })
        deps = result["depends_on"]
        self.assertEqual(deps["a"].value, {"condition": "service_healthy"})
        self.assertIsInstance(deps["b"], ResetTag)
        self.assertEqual(deps["c"], {"condition": "service_started"})

    def test_normalize_service_whole_reset_still_normalizes_rest(self) -> None:
        result = normalize_service({"depends_on": ResetTag(), "secrets": "s1"})
        self.assertIsInstance(result["depends_on"], ResetTag)
        self.assertEqual(result["secrets"], ["s1"])
