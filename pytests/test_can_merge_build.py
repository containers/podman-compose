# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import os
import unittest

import yaml
from parameterized import parameterized

from podman_compose import PodmanCompose
from podman_compose import normalize_service


class TestMergeBuild(unittest.TestCase):
    @parameterized.expand([
        ({"test": "test"}, {"test": "test"}),
        ({"build": "."}, {"build": {"context": "."}}),
        ({"build": "./dir-1"}, {"build": {"context": "./dir-1"}}),
        ({"build": {"context": "./dir-1"}}, {"build": {"context": "./dir-1"}}),
        (
            {"build": {"dockerfile": "dockerfile-1"}},
            {"build": {"dockerfile": "dockerfile-1"}},
        ),
        (
            {"build": {"context": "./dir-1", "dockerfile": "dockerfile-1"}},
            {"build": {"context": "./dir-1", "dockerfile": "dockerfile-1"}},
        ),
    ])
    def test_simple(self, input, expected):
        self.assertEqual(normalize_service(input), expected)

    @parameterized.expand([
        ({"test": "test"}, {"test": "test"}),
        ({"build": "."}, {"build": {"context": "./sub_dir/."}}),
        ({"build": "./dir-1"}, {"build": {"context": "./sub_dir/dir-1"}}),
        ({"build": {"context": "./dir-1"}}, {"build": {"context": "./sub_dir/dir-1"}}),
        (
            {"build": {"dockerfile": "dockerfile-1"}},
            {"build": {"context": "./sub_dir", "dockerfile": "dockerfile-1"}},
        ),
        (
            {"build": {"context": "./dir-1", "dockerfile": "dockerfile-1"}},
            {"build": {"context": "./sub_dir/dir-1", "dockerfile": "dockerfile-1"}},
        ),
    ])
    def test_normalize_service_with_sub_dir(self, input, expected):
        self.assertEqual(normalize_service(input, sub_dir="./sub_dir"), expected)

    @parameterized.expand([
        ({}, {}, {}),
        ({}, {"test": "test"}, {"test": "test"}),
        ({"test": "test"}, {}, {"test": "test"}),
        ({"test": "test-1"}, {"test": "test-2"}, {"test": "test-2"}),
        ({}, {"build": "."}, {"build": {"context": "."}}),
        ({"build": "."}, {}, {"build": {"context": "."}}),
        ({"build": "./dir-1"}, {"build": "./dir-2"}, {"build": {"context": "./dir-2"}}),
        ({}, {"build": {"context": "./dir-1"}}, {"build": {"context": "./dir-1"}}),
        ({"build": {"context": "./dir-1"}}, {}, {"build": {"context": "./dir-1"}}),
        (
            {"build": {"context": "./dir-1"}},
            {"build": {"context": "./dir-2"}},
            {"build": {"context": "./dir-2"}},
        ),
        (
            {},
            {"build": {"dockerfile": "dockerfile-1"}},
            {"build": {"dockerfile": "dockerfile-1"}},
        ),
        (
            {"build": {"dockerfile": "dockerfile-1"}},
            {},
            {"build": {"dockerfile": "dockerfile-1"}},
        ),
        (
            {"build": {"dockerfile": "./dockerfile-1"}},
            {"build": {"dockerfile": "./dockerfile-2"}},
            {"build": {"dockerfile": "./dockerfile-2"}},
        ),
        (
            {"build": {"dockerfile": "./dockerfile-1"}},
            {"build": {"context": "./dir-2"}},
            {"build": {"dockerfile": "./dockerfile-1", "context": "./dir-2"}},
        ),
        (
            {"build": {"dockerfile": "./dockerfile-1", "context": "./dir-1"}},
            {"build": {"dockerfile": "./dockerfile-2", "context": "./dir-2"}},
            {"build": {"dockerfile": "./dockerfile-2", "context": "./dir-2"}},
        ),
        (
            {"build": {"dockerfile": "./dockerfile-1"}},
            {"build": {"dockerfile": "./dockerfile-2", "args": ["ENV1=1"]}},
            {"build": {"dockerfile": "./dockerfile-2", "args": ["ENV1=1"]}},
        ),
        (
            {"build": {"dockerfile": "./dockerfile-2", "args": ["ENV1=1"]}},
            {"build": {"dockerfile": "./dockerfile-1"}},
            {"build": {"dockerfile": "./dockerfile-1", "args": ["ENV1=1"]}},
        ),
        (
            {"build": {"dockerfile": "./dockerfile-2", "args": ["ENV1=1"]}},
            {"build": {"dockerfile": "./dockerfile-1", "args": ["ENV2=2"]}},
            {"build": {"dockerfile": "./dockerfile-1", "args": ["ENV1=1", "ENV2=2"]}},
        ),
    ])
    def test_parse_compose_file_when_multiple_composes(self, input, override, expected):
        compose_test_1 = {"services": {"test-service": input}}
        compose_test_2 = {"services": {"test-service": override}}
        dump_yaml(compose_test_1, "test-compose-1.yaml")
        dump_yaml(compose_test_2, "test-compose-2.yaml")

        podman_compose = PodmanCompose()
        set_args(podman_compose, ["test-compose-1.yaml", "test-compose-2.yaml"])

        podman_compose._parse_compose_file()  # pylint: disable=protected-access

        actual_compose = {}
        if podman_compose.services:
            podman_compose.services["test-service"].pop("_deps")
            actual_compose = podman_compose.services["test-service"]
        self.assertEqual(actual_compose, expected)


def set_args(podman_compose: PodmanCompose, file_names: list[str]) -> None:
    podman_compose.global_args = argparse.Namespace()
    podman_compose.global_args.file = file_names
    podman_compose.global_args.project_name = None
    podman_compose.global_args.env_file = None
    podman_compose.global_args.profile = []
    podman_compose.global_args.in_pod = True
    podman_compose.global_args.no_normalize = True


def dump_yaml(compose: dict, name: str) -> None:
    with open(name, "w", encoding="utf-8") as outfile:
        yaml.safe_dump(compose, outfile, default_flow_style=False)


def test_clean_test_yamls() -> None:
    test_files = ["test-compose-1.yaml", "test-compose-2.yaml"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
