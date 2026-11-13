# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import argparse
import copy
import os
import tempfile
import unittest
from typing import Any

import yaml
from parameterized import parameterized

from podman_compose import PodmanCompose
from podman_compose import PodmanComposeError

SECTION_NAMES = ("networks", "volumes", "secrets", "configs")


def parse_compose_file(*composes: dict[str, Any] | str) -> PodmanCompose:
    with tempfile.TemporaryDirectory() as tmp_dir:
        compose_files = []
        for index, compose in enumerate(composes):
            compose_file = os.path.join(tmp_dir, f"docker-compose-{index}.yml")
            with open(compose_file, "w", encoding="utf-8") as f:
                if isinstance(compose, str):
                    f.write(compose)
                else:
                    yaml.safe_dump(compose, f)
            compose_files.append(compose_file)

        podman_compose = PodmanCompose()
        podman_compose.global_args = argparse.Namespace(
            file=compose_files,
            project_name="test_proj",
            env_file=None,
            profile=[],
            in_pod="false",
            pod_args=None,
            no_normalize=False,
        )
        podman_compose._parse_compose_file()
        return podman_compose


def misplaced_section_error(name: str) -> str:
    return (
        f"service `{name}` has no `image` or `build`. If it is meant to be the top-level "
        f"`{name}` section, it is indented under `services` by mistake."
    )


class TestMisplacedTopLevelSections(unittest.TestCase):
    def test_networks_indented_under_services(self) -> None:
        # the compose file from issue #1549
        compose_yaml = """
services:
  app:
    image: busybox
    networks:
      - mynet

  networks:
    mynet:
      driver: bridge
"""
        with self.assertRaises(PodmanComposeError) as cm:
            parse_compose_file(compose_yaml)
        self.assertEqual(str(cm.exception), misplaced_section_error("networks"))

    @parameterized.expand([
        ("networks", {"mynet": {"driver": "bridge"}}, {"networks": ["mynet"]}),
        ("volumes", {"data": None}, {"volumes": ["data:/data"]}),
        ("secrets", {"my_secret": {"file": "./my_secret.txt"}}, {"secrets": ["my_secret"]}),
        ("configs", {"my_config": {"file": "./my_config.txt"}}, {}),
    ])
    def test_section_indented_under_services(
        self, name: str, section: dict[str, Any], app_references: dict[str, Any]
    ) -> None:
        compose = {"services": {"app": {"image": "busybox", **app_references}, name: section}}
        with self.assertRaises(PodmanComposeError) as cm:
            parse_compose_file(compose)
        self.assertEqual(str(cm.exception), misplaced_section_error(name))

    @parameterized.expand([
        ("image", {"image": "busybox"}),
        ("build", {"build": "."}),
        ("extends", {"extends": "app"}),
        ("rootfs", {"x-podman.rootfs": "/path/to/rootfs", "command": ["/bin/busybox"]}),
    ])
    def test_service_named_like_a_section(self, _: str, service: dict[str, Any]) -> None:
        services = {name: copy.deepcopy(service) for name in SECTION_NAMES}
        compose = {"services": {"app": {"image": "busybox"}, **services}}
        podman_compose = parse_compose_file(compose)
        self.assertEqual(set(podman_compose.services), {"app", *SECTION_NAMES})

    @parameterized.expand([
        ("networks", {"image": {"driver": "bridge"}}, {"networks": ["image"]}),
        ("volumes", {"image": None}, {"volumes": ["image:/data"]}),
    ])
    def test_section_with_an_entry_named_image(
        self, name: str, section: dict[str, Any], app_references: dict[str, Any]
    ) -> None:
        compose = {"services": {"app": {"image": "busybox", **app_references}, name: section}}
        with self.assertRaises(PodmanComposeError) as cm:
            parse_compose_file(compose)
        self.assertEqual(str(cm.exception), misplaced_section_error(name))

    def test_image_from_a_later_compose_file(self) -> None:
        base = {"services": {"app": {"image": "busybox"}, "volumes": {"command": ["true"]}}}
        override = {"services": {"volumes": {"image": "busybox"}}}
        podman_compose = parse_compose_file(base, override)
        self.assertEqual(set(podman_compose.services), {"app", "volumes"})
