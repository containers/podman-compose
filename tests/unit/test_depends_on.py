import unittest
from typing import Any

from parameterized import parameterized

from podman_compose import flat_deps


class TestDependsOn(unittest.TestCase):
    @parameterized.expand([
        (
            {
                "service_a": {},
                "service_b": {"depends_on": {"service_a": {"condition": "healthy"}}},
                "service_c": {"depends_on": {"service_b": {"condition": "healthy"}}},
            },
            # dependencies
            {
                "service_a": set(),
                "service_b": set(["service_a"]),
                "service_c": set(["service_a", "service_b"]),
            },
            # dependents
            {
                "service_a": set(["service_b", "service_c"]),
                "service_b": set(["service_c"]),
                "service_c": set(),
            },
        ),
    ])
    def test_flat_deps(
        self,
        services: dict[str, Any],
        deps: dict[str, set[str]],
        dependents: dict[str, set[str]],
    ) -> None:
        flat_deps(services)
        self.assertEqual(
            {
                name: set([x.name for x in value.get("_deps", set())])
                for name, value in services.items()
            },
            deps,
            msg="Dependencies do not match",
        )
        self.assertEqual(
            {
                name: set([x.name for x in value.get("_dependents", set())])
                for name, value in services.items()
            },
            dependents,
            msg="Dependents do not match",
        )
