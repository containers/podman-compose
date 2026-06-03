# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import argparse
import os
import unittest
from typing import Any

import yaml

from podman_compose import PodmanCompose


class TestIncludeDict(unittest.TestCase):
    def setUp(self) -> None:
        self.test_files: list[str] = []

    def tearDown(self) -> None:
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)

    def write_yaml(self, name: str, content: dict[str, Any]) -> None:
        with open(name, "w", encoding="utf-8") as f:
            yaml.safe_dump(content, f)
        self.test_files.append(name)

    def test_parse_compose_file_with_include_dict(self) -> None:
        # 1. Create a base compose file to be included
        include_content = {"services": {"base_web": {"image": "nginx:alpine"}}}
        self.write_yaml("test-compose-include.yaml", include_content)

        # 2. Create a main compose file with include detailed format (dictionary)
        main_content = {
            "version": "3.8",
            "include": [{"path": "./test-compose-include.yaml"}],
            "services": {"web": {"image": "alpine:latest"}},
        }
        self.write_yaml("test-compose-main.yaml", main_content)

        podman_compose = PodmanCompose()
        podman_compose.global_args = argparse.Namespace()
        podman_compose.global_args.file = ["test-compose-main.yaml"]
        podman_compose.global_args.project_name = "test_project"
        podman_compose.global_args.env_file = None
        podman_compose.global_args.profile = []
        podman_compose.global_args.in_pod = "false"
        podman_compose.global_args.pod_args = None
        podman_compose.global_args.no_normalize = True

        # It should run successfully without raising a TypeError
        podman_compose._parse_compose_file()

        self.assertIn("web", podman_compose.services)
        self.assertIn("base_web", podman_compose.services)
