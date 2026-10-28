# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from typing import Any

from podman_compose import PodmanCompose


def _services(compose_yaml: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = os.path.join(tmp_dir, "docker-compose.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(compose_yaml)
        podman_compose = PodmanCompose()
        podman_compose.global_args = argparse.Namespace(
            file=[path],
            project_name="test_proj",
            env_file=None,
            profile=[],
            in_pod="false",
            pod_args=None,
            no_normalize=False,
        )
        podman_compose._parse_compose_file()
        return podman_compose.services


class TestExtendsBaseIsolation(unittest.TestCase):
    def test_child_does_not_change_base(self) -> None:
        services = _services(
            """
services:
    base:
        image: busybox
        deploy:
            resources:
                limits:
                    memory: 64m
    child:
        extends: base
        deploy:
            resources:
                limits:
                    cpus: "0.5"
"""
        )
        self.assertEqual(services["base"]["deploy"], {"resources": {"limits": {"memory": "64m"}}})
        self.assertEqual(
            services["child"]["deploy"],
            {"resources": {"limits": {"memory": "64m", "cpus": "0.5"}}},
        )

    def test_children_do_not_change_each_other(self) -> None:
        services = _services(
            """
services:
    base:
        image: busybox
        build:
            context: .
            args:
                COMMON: "1"
    first:
        extends: base
        build:
            args:
                FIRST: "1"
    second:
        extends: base
        build:
            args:
                SECOND: "1"
"""
        )
        self.assertEqual(services["base"]["build"]["args"], ["COMMON=1"])
        self.assertEqual(services["first"]["build"]["args"], ["COMMON=1", "FIRST=1"])
        self.assertEqual(services["second"]["build"]["args"], ["COMMON=1", "SECOND=1"])
