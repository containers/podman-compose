# SPDX-License-Identifier: GPL-2.0

from __future__ import annotations

import textwrap
import unittest
from unittest import mock

import yaml

from podman_compose import build_compose_config


class TestBuildComposeConfig(unittest.TestCase):
    def _create_compose_mock(
        self,
        services: dict | None = None,
        networks: dict | None = None,
        default_net: str | None = "default",
        merged_yaml: str | None = None,
    ) -> mock.Mock:
        compose = mock.Mock()
        compose.project_name = "test_project"
        compose.services = services or {}
        compose.networks = networks or {}
        compose.default_net = default_net
        compose.x_podman = {}
        compose.original_configuration = lambda x: x
        compose.format_name = mock.Mock(side_effect=lambda *args: "_".join(["test_project", *args]))
        compose.join_name_parts = mock.Mock(side_effect=lambda *args: "_".join(args))
        compose.merged_yaml = merged_yaml or ""
        return compose

    def dump_yaml(self, compose: mock.Mock) -> str:
        return yaml.safe_dump(build_compose_config(compose), sort_keys=False)

    def test_default_network_injected_when_service_has_no_networks(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            networks={"default": None},
            default_net="default",
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      default: null
                networks:
                  default:
                    name: test_project_default
                """),
        )

    def test_no_default_network_injected_when_service_has_network_mode(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "network_mode": "host"}},
            networks={"default": None},
            default_net="default",
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    network_mode: host
                """),
        )

    def test_no_default_network_injected_when_service_has_networks(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": {"custom": None}}},
            networks={"custom": None},
            default_net=None,
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      custom: null
                networks:
                  custom:
                    name: test_project_custom
                """),
        )

    def test_non_external_network_gets_project_name(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            networks={"default": None},
            default_net="default",
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      default: null
                networks:
                  default:
                    name: test_project_default
                """),
        )

    def test_unused_external_network_is_omitted(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            networks={"ext": {"external": True}},
            default_net=None,
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                """),
        )

    def test_external_network_gets_original_name(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": ["ext"]}},
            networks={"ext": {"external": True}},
            default_net=None,
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      ext: null
                networks:
                  ext:
                    external: true
                    name: ext
                """),
        )

    def test_external_network_dict_with_custom_name(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": ["ext"]}},
            networks={"ext": {"external": {"name": "actual-net"}}},
            default_net=None,
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      ext: null
                networks:
                  ext:
                    external:
                      name: actual-net
                    name: actual-net
                """),
        )

    def test_list_networks_converted_to_dict(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": ["net0"]}},
            networks={"net0": None},
            default_net=None,
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      net0: null
                networks:
                  net0:
                    name: test_project_net0
                """),
        )

    def test_dict_networks_with_empty_dict_converted_to_null(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": {"net0": {}}}},
            networks={"net0": None},
            default_net=None,
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      net0: null
                networks:
                  net0:
                    name: test_project_net0
                """),
        )

    def test_dict_networks_with_values_preserved(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "networks": {"net0": {"aliases": ["web"]}}}},
            networks={"net0": None},
            default_net=None,
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      net0:
                        aliases:
                        - web
                networks:
                  net0:
                    name: test_project_net0
                """),
        )

    def test_network_mode_none_no_default_network_injected(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx", "network_mode": "none"}},
            networks={"default": None},
            default_net="default",
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    network_mode: none
                """),
        )

    def test_custom_top_level_keys_preserved(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            networks={"default": None},
            default_net="default",
            merged_yaml="name: my-project\nx-custom: some-value\nconfigs:\n  my_config:\n    "
            "file: ./config.txt\n",
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      default: null
                name: my-project
                x-custom: some-value
                configs:
                  my_config:
                    file: ./config.txt
                networks:
                  default:
                    name: test_project_default
                """),
        )

    def test_merged_yaml_volumes_and_secrets_preserved(self) -> None:
        compose = self._create_compose_mock(
            services={"web": {"image": "nginx"}},
            merged_yaml="volumes:\n  data:\n    driver: local\nsecrets:\n  my_secret:\n    "
            "external: true\n",
        )
        self.assertEqual(
            self.dump_yaml(compose),
            textwrap.dedent("""\
                services:
                  web:
                    image: nginx
                    networks:
                      default: null
                volumes:
                  data:
                    driver: local
                secrets:
                  my_secret:
                    external: true
                """),
        )
