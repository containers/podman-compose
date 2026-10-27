# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import os
import tempfile
import unittest

from podman_compose import PodmanCompose
from podman_compose import effective_profiles


def _parse(compose_yaml: str, profile: list[str] | None = None) -> PodmanCompose:
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
        return podman_compose


INHERITED = """
services:
    base:
        image: busybox
        environment: [FROM_BASE=1]
        profiles: [inherited]
    child:
        extends: base
    other:
        image: busybox
"""

OWN_PROFILE = """
services:
    base:
        image: busybox
        profiles: [p1]
    child:
        extends:
            service: base
        profiles: [p2]
"""

CHAIN = """
services:
    grand:
        image: busybox
        environment: [A=1]
        profiles: [g]
    base:
        extends: grand
        environment: [B=1]
    child:
        extends: base
        profiles: [c]
"""


class TestEffectiveProfiles(unittest.TestCase):
    def test_inherits_base_profiles_first(self) -> None:
        services = {
            "base": {"profiles": ["p1"]},
            "child": {"extends": "base", "profiles": ["p2", "p1"]},
        }
        self.assertEqual(effective_profiles(services)["child"], ["p1", "p2"])

    def test_follows_chain(self) -> None:
        services = {
            "grand": {"profiles": ["g"]},
            "base": {"extends": {"service": "grand"}},
            "child": {"extends": "base"},
        }
        self.assertEqual(effective_profiles(services)["child"], ["g"])

    def test_ignores_extends_from_other_file(self) -> None:
        services = {
            "base": {"profiles": ["p1"]},
            "child": {"extends": {"file": "other.yml", "service": "base"}},
        }
        self.assertEqual(effective_profiles(services)["child"], [])

    def test_survives_cycle(self) -> None:
        services = {
            "a": {"extends": "b", "profiles": ["pa"]},
            "b": {"extends": "a", "profiles": ["pb"]},
        }
        profiles = effective_profiles(services)
        self.assertIn("pa", profiles["a"])
        self.assertIn("pb", profiles["b"])


class TestExtendsWithProfiles(unittest.TestCase):
    def test_child_of_inactive_base_is_inactive(self) -> None:
        compose = _parse(INHERITED)
        self.assertEqual(list(compose.services), ["other"])

    def test_profile_activates_child_and_base(self) -> None:
        compose = _parse(INHERITED, ["inherited"])
        self.assertEqual(sorted(compose.services), ["base", "child", "other"])
        self.assertEqual(compose.services["child"]["environment"], {"FROM_BASE": "1"})

    def test_child_resolves_against_inactive_base(self) -> None:
        compose = _parse(OWN_PROFILE, ["p2"])
        self.assertEqual(list(compose.services), ["child"])
        self.assertEqual(compose.services["child"]["image"], "busybox")
        self.assertEqual(compose.services["child"]["profiles"], ["p1", "p2"])

    def test_declared_profiles_include_inherited(self) -> None:
        compose = _parse(INHERITED)
        self.assertEqual(compose.declared_profiles, ["inherited"])

    def test_chain_through_inactive_services(self) -> None:
        compose = _parse(CHAIN, ["c"])
        self.assertEqual(list(compose.services), ["child"])
        self.assertEqual(compose.services["child"]["environment"], {"A": "1", "B": "1"})

    def test_chain_without_profiles(self) -> None:
        compose = _parse(
            """
services:
    a:
        image: busybox
    b:
        extends: a
    c:
        extends: b
    d:
        extends: c
"""
        )
        self.assertEqual(sorted(compose.services), ["a", "b", "c", "d"])
        self.assertEqual(compose.services["d"]["image"], "busybox")
