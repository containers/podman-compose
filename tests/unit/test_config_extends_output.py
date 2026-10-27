# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import os
import tempfile
import unittest

import yaml

from podman_compose import PodmanCompose


def _merged(compose_yaml: str, profile: list[str] | None = None) -> dict:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "docker-compose.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(compose_yaml)
        podman_compose = PodmanCompose()
        podman_compose.global_args = argparse.Namespace(
            file=[path],
            project_name="test_proj",
            env_file=None,
            profile=profile or [],
            in_pod="false",
            pod_args=None,
            no_normalize=False,
        )
        podman_compose._parse_compose_file()
        return yaml.safe_load(podman_compose.merged_yaml)


class TestConfigExtendsOutput(unittest.TestCase):
    def test_prints_inherited_settings(self) -> None:
        merged = _merged(
            """
services:
    base:
        image: busybox
        environment: [A=1]
    child:
        extends: base
        environment: [B=1]
"""
        )
        self.assertEqual(
            merged["services"]["child"],
            {"image": "busybox", "environment": {"A": "1", "B": "1"}},
        )

    def test_prints_chain_without_extends_key(self) -> None:
        merged = _merged(
            """
services:
    a:
        image: busybox
        environment: [A=1]
    b:
        extends: a
    c:
        extends:
            service: b
        environment: [C=1]
"""
        )
        self.assertEqual(
            merged["services"]["c"],
            {"image": "busybox", "environment": {"A": "1", "C": "1"}},
        )

    def test_omits_internal_keys(self) -> None:
        merged = _merged(
            """
services:
    db:
        image: busybox
    web:
        image: busybox
        depends_on: [db]
        links: [db]
"""
        )
        for service in merged["services"].values():
            self.assertFalse([key for key in service if key.startswith("_")])

    def test_omits_inactive_base(self) -> None:
        merged = _merged(
            """
services:
    base:
        image: busybox
        profiles: [p1]
    child:
        extends: base
        profiles: [p2]
""",
            ["p2"],
        )
        self.assertEqual(list(merged["services"]), ["child"])
        self.assertEqual(merged["services"]["child"]["image"], "busybox")
        self.assertEqual(merged["services"]["child"]["profiles"], ["p1", "p2"])
