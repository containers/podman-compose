# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import os
import unittest
from typing import Any

import yaml
from parameterized import parameterized

from podman_compose import PodmanCompose


class TestIncludeDict(unittest.TestCase):
    def setUp(self) -> None:
        self.test_files: list[str] = []
        self.podman_compose = PodmanCompose()
        self.podman_compose.global_args.file = ["test-compose-main.yaml"]
        self.podman_compose.global_args.project_name = "test_project"
        self.podman_compose.global_args.env_file = None
        self.podman_compose.global_args.profile = []
        self.podman_compose.global_args.in_pod = "false"

    def tearDown(self) -> None:
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)

    def write_yaml(self, name: str, content: dict[str, Any]) -> None:
        with open(name, "w", encoding="utf-8") as f:
            yaml.safe_dump(content, f)
        self.test_files.append(name)

    @parameterized.expand([
        ("string", ["./test-compose-include.yaml"], ["base_web"]),
        ("dict_path_string", [{"path": "./test-compose-include.yaml"}], ["base_web"]),
        (
            "dict_path_list",
            [{"path": ["./test-compose-include.yaml", "./test-compose-include-2.yaml"]}],
            ["base_web", "base_web-2"],
        ),
        ("empty", [{"path": []}], []),
    ])
    def test_parse_compose_file_include(
        self, name: str, include_value: list, expected_included_services: list
    ) -> None:
        include_content = {"services": {"base_web": {"image": "nginx:alpine"}}}
        self.write_yaml("test-compose-include.yaml", include_content)

        include_content_2 = {"services": {"base_web-2": {"image": "nginx:alpine"}}}
        self.write_yaml("test-compose-include-2.yaml", include_content_2)

        main_content = {
            "include": include_value,
            "services": {"web": {"image": "alpine:latest"}},
        }
        self.write_yaml("test-compose-main.yaml", main_content)

        self.podman_compose._parse_compose_file()

        self.assertIn("web", self.podman_compose.services)

        for svc in expected_included_services:
            self.assertIn(svc, self.podman_compose.services)

    @parameterized.expand([
        ("not_a_list", {"path": {"./test-compose-include.yaml"}}, "`include` must be a list"),
        (
            "no_path_key",
            [{"not_path": "./test-compose-include.yaml"}],
            "Missing required 'path' key in `include` block",
        ),
        ("path_not_list_or_string", [{"path": {}}], "'path' must be a string or a list of strings"),
        (
            "item_wrong_format",
            [["./test-compose-include.yaml"]],
            "Items in `include` must be strings or dictionaries with a 'path' key",
        ),
    ])
    def test_parse_compose_file_include_errors(
        self, name: str, include_value: dict | list, exception_msg: str
    ) -> None:
        main_content = {
            "include": include_value,
            "services": {"web": {"image": "alpine:latest"}},
        }
        self.write_yaml("test-compose-main.yaml", main_content)

        with self.assertRaises(RuntimeError) as cm:
            self.podman_compose._parse_compose_file()
        self.assertEqual(str(cm.exception), exception_msg)
