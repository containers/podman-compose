# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import os
import tempfile
import unittest

from podman_compose import PodmanCompose


def parse_compose(content: str, profiles: list[str]) -> PodmanCompose:
    with tempfile.TemporaryDirectory() as tmp_dir:
        compose_file = os.path.join(tmp_dir, "docker-compose.yaml")
        with open(compose_file, "w", encoding="utf-8") as f:
            f.write(content)

        podman_compose = PodmanCompose()
        podman_compose.global_args = argparse.Namespace(
            file=[compose_file],
            project_name="test_proj",
            env_file=None,
            profile=profiles,
            in_pod="false",
            pod_args=None,
            no_normalize=False,
        )
        podman_compose._parse_compose_file()
        return podman_compose


class TestExtendsProfiles(unittest.TestCase):
    def test_extends_service_disabled_by_profile(self) -> None:
        compose = parse_compose(
            """
services:
    base:
        profiles: [_base]
        image: busybox
        environment:
            VAR_BASE: "base"
    app:
        extends: base
        profiles: [app]
        command: echo hello
""",
            ["app"],
        )

        self.assertEqual(list(compose.services), ["app"])
        app = compose.services["app"]
        self.assertEqual(app["image"], "busybox")
        self.assertEqual(app["environment"], {"VAR_BASE": "base"})
        self.assertEqual(app["command"], "echo hello")
        self.assertEqual(app["_deps"], set())

    def test_extends_service_disabled_by_profile_without_own_profile(self) -> None:
        compose = parse_compose(
            """
services:
    base:
        profiles: [_base]
        image: busybox
    app:
        extends:
            service: base
        command: echo hello
""",
            [],
        )

        self.assertEqual(list(compose.services), ["app"])
        self.assertEqual(compose.services["app"]["image"], "busybox")

    def test_extends_only_services_follows_chain(self) -> None:
        defined = {
            "root": {"profiles": ["_base"]},
            "base": {"profiles": ["_base"], "extends": {"service": "root"}},
            "other": {"profiles": ["_base"]},
            "app": {"extends": "base"},
            "from_file": {"extends": {"service": "other", "file": "common.yaml"}},
        }
        enabled = {name: defined[name] for name in ("app", "from_file")}

        extends_only = PodmanCompose._resolve_extends_only_services(defined, enabled)

        self.assertEqual(set(extends_only), {"root", "base"})

    def test_extends_unknown_service(self) -> None:
        with self.assertRaises(KeyError):
            parse_compose(
                """
services:
    app:
        extends: missing
        image: busybox
""",
                [],
            )
