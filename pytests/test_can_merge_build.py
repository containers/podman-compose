# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import copy
import os
import unittest

import yaml
from parameterized import parameterized

from podman_compose import PodmanCompose


class TestCanMergeBuild(unittest.TestCase):
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

    # $$$ is a placeholder for either command or entrypoint
    @parameterized.expand([
        ({}, {"$$$": []}, {"$$$": []}),
        ({"$$$": []}, {}, {"$$$": []}),
        ({"$$$": []}, {"$$$": "sh-2"}, {"$$$": ["sh-2"]}),
        ({"$$$": "sh-2"}, {"$$$": []}, {"$$$": []}),
        ({}, {"$$$": "sh"}, {"$$$": ["sh"]}),
        ({"$$$": "sh"}, {}, {"$$$": ["sh"]}),
        ({"$$$": "sh-1"}, {"$$$": "sh-2"}, {"$$$": ["sh-2"]}),
        ({"$$$": ["sh-1"]}, {"$$$": "sh-2"}, {"$$$": ["sh-2"]}),
        ({"$$$": "sh-1"}, {"$$$": ["sh-2"]}, {"$$$": ["sh-2"]}),
        ({"$$$": "sh-1"}, {"$$$": ["sh-2", "sh-3"]}, {"$$$": ["sh-2", "sh-3"]}),
        ({"$$$": ["sh-1"]}, {"$$$": ["sh-2", "sh-3"]}, {"$$$": ["sh-2", "sh-3"]}),
        ({"$$$": ["sh-1", "sh-2"]}, {"$$$": ["sh-3", "sh-4"]}, {"$$$": ["sh-3", "sh-4"]}),
        ({}, {"$$$": ["sh-3", "sh      4"]}, {"$$$": ["sh-3", "sh      4"]}),
        ({"$$$": "sleep infinity"}, {"$$$": "sh"}, {"$$$": ["sh"]}),
        ({"$$$": "sh"}, {"$$$": "sleep infinity"}, {"$$$": ["sleep", "infinity"]}),
        (
            {},
            {"$$$": "bash -c 'sleep infinity'"},
            {"$$$": ["bash", "-c", "sleep infinity"]},
        ),
    ])
    def test_parse_compose_file_when_multiple_composes_keys_command_entrypoint(
        self, base_template, override_template, expected_template
    ):
        for key in ['command', 'entrypoint']:
            base, override, expected = template_to_expression(
                base_template, override_template, expected_template, key
            )
            compose_test_1 = {"services": {"test-service": base}}
            compose_test_2 = {"services": {"test-service": override}}
            dump_yaml(compose_test_1, "test-compose-1.yaml")
            dump_yaml(compose_test_2, "test-compose-2.yaml")

            podman_compose = PodmanCompose()
            set_args(podman_compose, ["test-compose-1.yaml", "test-compose-2.yaml"])

            podman_compose._parse_compose_file()  # pylint: disable=protected-access

            actual = {}
            if podman_compose.services:
                podman_compose.services["test-service"].pop("_deps")
                actual = podman_compose.services["test-service"]
            self.assertEqual(actual, expected)


def set_args(podman_compose: PodmanCompose, file_names: list[str]) -> None:
    podman_compose.global_args = argparse.Namespace()
    podman_compose.global_args.file = file_names
    podman_compose.global_args.project_name = None
    podman_compose.global_args.env_file = None
    podman_compose.global_args.profile = []
    podman_compose.global_args.in_pod_bool = True
    podman_compose.global_args.no_normalize = True


def dump_yaml(compose: dict, name: str) -> None:
    with open(name, "w", encoding="utf-8") as outfile:
        yaml.safe_dump(compose, outfile, default_flow_style=False)


def template_to_expression(base, override, expected, key):
    base_copy = copy.deepcopy(base)
    override_copy = copy.deepcopy(override)
    expected_copy = copy.deepcopy(expected)

    expected_copy[key] = expected_copy.pop("$$$")
    if "$$$" in base:
        base_copy[key] = base_copy.pop("$$$")
    if "$$$" in override:
        override_copy[key] = override_copy.pop("$$$")
    return base_copy, override_copy, expected_copy


def test_clean_test_yamls() -> None:
    test_files = ["test-compose-1.yaml", "test-compose-2.yaml"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
