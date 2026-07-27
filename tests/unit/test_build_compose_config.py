# SPDX-License-Identifier: GPL-2.0

from __future__ import annotations

import unittest
from unittest import mock

from podman_compose import build_compose_config


class TestBuildComposeConfig(unittest.TestCase):
    def _create_compose_mock(
        self,
        services: dict | None = None,
        networks: dict | None = None,
        default_net: str | None = "default",
    ) -> mock.Mock:
        compose = mock.Mock()
        compose.project_name = "test_project"
        compose.services = services or {}
        compose.networks = networks or {}
        compose.default_net = default_net
        compose.vols = {}
        compose.declared_secrets = {}
        compose.original_configuration = lambda x: x
        return compose

    def test_default_network_injected_when_service_has_no_networks(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            networks={"default": None},
            default_net="default",
        )
        config = build_compose_config(compose)
        self.assertEqual(config["services"]["web"]["networks"], {"default": None})

    def test_no_default_network_injected_when_service_has_network_mode(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "network_mode": "host"}},
            networks={"default": None},
            default_net="default",
        )
        config = build_compose_config(compose)
        self.assertNotIn("networks", config["services"]["web"])
        self.assertEqual(config["services"]["web"]["network_mode"], "host")

    def test_no_default_network_injected_when_service_has_networks(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": {"custom": None}}},
            networks={"custom": None},
            default_net=None,
        )
        config = build_compose_config(compose)
        self.assertEqual(config["services"]["web"]["networks"], {"custom": None})
        self.assertNotIn("default", config["services"]["web"])

    def test_non_external_network_gets_project_name(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            networks={"default": None},
            default_net="default",
        )
        compose.format_name = mock.Mock(return_value="test_project_default")
        config = build_compose_config(compose)
        self.assertEqual(config["networks"]["default"]["name"], "test_project_default")

    def test_external_network_does_not_get_project_name(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            networks={"ext": {"external": True}},
            default_net=None,
        )
        config = build_compose_config(compose)
        self.assertNotIn("networks", config)

    def test_external_network_gets_original_name(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": ["ext"]}},
            networks={"ext": {"external": True}},
            default_net=None,
        )
        compose.format_name = mock.Mock(return_value="test_project_ext")
        config = build_compose_config(compose)
        self.assertEqual(config["networks"]["ext"]["name"], "ext")
        self.assertTrue(config["networks"]["ext"]["external"])

    def test_list_networks_converted_to_dict(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": ["net0"]}},
            networks={"net0": None},
            default_net=None,
        )
        config = build_compose_config(compose)
        self.assertEqual(config["services"]["web"]["networks"], {"net0": None})

    def test_dict_networks_with_empty_dict_converted_to_null(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": {"net0": {}}}},
            networks={"net0": None},
            default_net=None,
        )
        config = build_compose_config(compose)
        self.assertEqual(config["services"]["web"]["networks"], {"net0": None})

    def test_dict_networks_with_values_preserved(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": {"net0": {"aliases": ["web"]}}}},
            networks={"net0": None},
            default_net=None,
        )
        config = build_compose_config(compose)
        self.assertEqual(config["services"]["web"]["networks"], {"net0": {"aliases": ["web"]}})
