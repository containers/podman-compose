import subprocess
import unittest
from typing import Any
from unittest import mock

from parameterized import parameterized

from podman_compose import ServiceDependency
from podman_compose import check_dep_conditions
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

    def test_depends_on_properties(self) -> None:
        services: dict[str, Any] = {
            "service_a": {},
            "service_b": {
                "depends_on": {
                    "service_a": {
                        "condition": "service_healthy",
                        "required": False,
                        "restart": False,
                    }
                }
            },
        }
        flat_deps(services)
        self.assertEqual(
            services["service_b"]["_deps"],
            {ServiceDependency("service_a", "service_healthy", required=False, restart=False)},
        )


class TestCheckDepConditions(unittest.IsolatedAsyncioTestCase):
    async def test_empty_deps_does_nothing(self) -> None:
        """check_dep_conditions with empty deps should return without any waits"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock()

        await check_dep_conditions(compose, set())

        compose.podman.output.assert_not_called()

    async def test_per_container_wait_single_condition(self) -> None:
        """Each container gets its own podman wait call, not batched together"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock(return_value=b'[{"State":{"ExitCode":0}}]')
        compose.podman_version = None
        compose.container_names_by_service = {
            "srva": ["cnt_a1", "cnt_a2"],
        }
        deps = {
            ServiceDependency("srva", "service_completed_successfully"),
        }

        await check_dep_conditions(compose, deps)

        wait_calls = [c.args for c in compose.podman.output.call_args_list if c.args[1] == "wait"]
        self.assertEqual(
            wait_calls,
            [
                ([], "wait", ["--condition=stopped", "cnt_a1"]),
                ([], "wait", ["--condition=stopped", "cnt_a2"]),
            ],
        )

    async def test_per_container_wait_multiple_conditions(self) -> None:
        """Each condition's containers get individual wait calls"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock(return_value=b'[{"State":{"ExitCode":0}}]')
        compose.podman_version = None
        compose.container_names_by_service = {
            "srva": ["cnt_a"],
            "srvb": ["cnt_b"],
        }
        deps = {
            ServiceDependency("srva", "service_completed_successfully"),
            ServiceDependency("srvb", "service_started"),
        }

        await check_dep_conditions(compose, deps)

        wait_calls = [c.args for c in compose.podman.output.call_args_list if c.args[1] == "wait"]
        self.assertEqual(
            wait_calls,
            [
                ([], "wait", ["--condition=running", "cnt_b"]),
                ([], "wait", ["--condition=stopped", "cnt_a"]),
            ],
        )

    async def test_retry_on_error(self) -> None:
        """podman wait failure is retried (not fatal)"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock()
        compose.podman.output.side_effect = [
            b"running",  # inspect poll in _validate_completed_successfully
            subprocess.CalledProcessError(1, "podman wait", b"", b"error"),
            b"running",  # retry: inspect poll
            b'[{"State":{"ExitCode":0}}]',  # retry: wait succeeds
            b'[{"State":{"ExitCode":0}}]',  # inspect per container
        ]
        compose.podman_version = None
        compose.container_names_by_service = {
            "srva": ["cnt_a"],
        }
        deps = {
            ServiceDependency("srva", "service_completed_successfully"),
        }

        await check_dep_conditions(compose, deps)

        self.assertGreater(compose.podman.output.call_count, 1)

    async def test_skips_healthy_below_4_6_0(self) -> None:
        """Healthcheck condition is skipped on podman < 4.6.0"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock()
        compose.podman_version = "4.5.0"
        compose.container_names_by_service = {
            "srva": ["cnt_a"],
        }
        deps = {
            ServiceDependency("srva", "service_healthy"),
        }

        await check_dep_conditions(compose, deps)

        compose.podman.output.assert_not_called()

    async def test_skips_unhealthy_below_4_6_0(self) -> None:
        """UNHEALTHY condition is also skipped on podman < 4.6.0"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock()
        compose.podman_version = "4.5.0"
        compose.container_names_by_service = {
            "srva": ["cnt_a"],
        }
        deps = {
            ServiceDependency("srva", "unhealthy"),
        }

        await check_dep_conditions(compose, deps)

        compose.podman.output.assert_not_called()

    async def test_healthcheck_on_4_6_0_or_newer(self) -> None:
        """HEALTHY waits normally on podman >= 4.6.0 (not skipped)"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock()
        compose.podman_version = "4.6.0"
        compose.container_names_by_service = {
            "srva": ["cnt_a"],
        }
        deps = {
            ServiceDependency("srva", "service_healthy"),
        }

        await check_dep_conditions(compose, deps)

        calls = [c.args for c in compose.podman.output.call_args_list]
        self.assertEqual(
            calls,
            [
                ([], "wait", ["--condition=healthy", "cnt_a"]),
            ],
        )

    async def test_healthcheck_when_podman_version_none(self) -> None:
        """When podman_version is None, healthcheck is not skipped
        (the version gate short-circuits: None is not < 4.6.0)"""
        compose = mock.Mock()
        compose.podman.output = mock.AsyncMock()
        compose.podman_version = None
        compose.container_names_by_service = {
            "srva": ["cnt_a"],
        }
        deps = {
            ServiceDependency("srva", "service_healthy"),
        }

        await check_dep_conditions(compose, deps)

        calls = [c.args for c in compose.podman.output.call_args_list]
        self.assertEqual(
            calls,
            [
                ([], "wait", ["--condition=healthy", "cnt_a"]),
            ],
        )
