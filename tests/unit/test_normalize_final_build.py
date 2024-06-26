# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import argparse
import os
import unittest

import yaml
from parameterized import parameterized

from podman_compose import PodmanCompose
from podman_compose import normalize_final
from podman_compose import normalize_service_final

cwd = os.path.abspath(".")


class TestNormalizeFinalBuild(unittest.TestCase):
    cases_simple_normalization = [
        ({"image": "test-image"}, {"image": "test-image"}),
        (
            {"build": "."},
            {
                "build": {"context": cwd},
            },
        ),
        (
            {"build": "../relative"},
            {
                "build": {
                    "context": os.path.normpath(os.path.join(cwd, "../relative")),
                },
            },
        ),
        (
            {"build": "./relative"},
            {
                "build": {
                    "context": os.path.normpath(os.path.join(cwd, "./relative")),
                },
            },
        ),
        (
            {"build": "/workspace/absolute"},
            {
                "build": {
                    "context": "/workspace/absolute",
                },
            },
        ),
        (
            {
                "build": {
                    "dockerfile": "Dockerfile",
                },
            },
            {
                "build": {
                    "context": cwd,
                    "dockerfile": "Dockerfile",
                },
            },
        ),
        (
            {
                "build": {
                    "context": ".",
                },
            },
            {
                "build": {
                    "context": cwd,
                },
            },
        ),
        (
            {
                "build": {"context": "../", "dockerfile": "test-dockerfile"},
            },
            {
                "build": {
                    "context": os.path.normpath(os.path.join(cwd, "../")),
                    "dockerfile": "test-dockerfile",
                },
            },
        ),
        (
            {
                "build": {"context": ".", "dockerfile": "./dev/test-dockerfile"},
            },
            {
                "build": {
                    "context": cwd,
                    "dockerfile": "./dev/test-dockerfile",
                },
            },
        ),
    ]

    @parameterized.expand(cases_simple_normalization)
    def test_normalize_service_final_returns_absolute_path_in_context(self, input, expected):
        # Tests that [service.build] is normalized after merges
        project_dir = cwd
        self.assertEqual(normalize_service_final(input, project_dir), expected)

    @parameterized.expand(cases_simple_normalization)
    def test_normalize_returns_absolute_path_in_context(self, input, expected):
        project_dir = cwd
        compose_test = {"services": {"test-service": input}}
        compose_expected = {"services": {"test-service": expected}}
        self.assertEqual(normalize_final(compose_test, project_dir), compose_expected)

    @parameterized.expand(cases_simple_normalization)
    def test_parse_compose_file_when_single_compose(self, input, expected):
        compose_test = {"services": {"test-service": input}}
        dump_yaml(compose_test, "test-compose.yaml")

        podman_compose = PodmanCompose()
        set_args(podman_compose, ["test-compose.yaml"], no_normalize=None)

        podman_compose._parse_compose_file()

        actual_compose = {}
        if podman_compose.services:
            podman_compose.services["test-service"].pop("_deps")
            actual_compose = podman_compose.services["test-service"]
        self.assertEqual(actual_compose, expected)

    @parameterized.expand([
        (
            {},
            {"build": "."},
            {"build": {"context": cwd}},
        ),
        (
            {"build": "."},
            {},
            {"build": {"context": cwd}},
        ),
        (
            {"build": "/workspace/absolute"},
            {"build": "./relative"},
            {
                "build": {
                    "context": os.path.normpath(os.path.join(cwd, "./relative")),
                }
            },
        ),
        (
            {"build": "./relative"},
            {"build": "/workspace/absolute"},
            {"build": {"context": "/workspace/absolute"}},
        ),
        (
            {"build": "./relative"},
            {"build": "/workspace/absolute"},
            {"build": {"context": "/workspace/absolute"}},
        ),
        (
            {"build": {"dockerfile": "test-dockerfile"}},
            {},
            {"build": {"context": cwd, "dockerfile": "test-dockerfile"}},
        ),
        (
            {},
            {"build": {"dockerfile": "test-dockerfile"}},
            {"build": {"context": cwd, "dockerfile": "test-dockerfile"}},
        ),
        (
            {},
            {"build": {"dockerfile": "test-dockerfile"}},
            {"build": {"context": cwd, "dockerfile": "test-dockerfile"}},
        ),
        (
            {"build": {"dockerfile": "test-dockerfile-1"}},
            {"build": {"dockerfile": "test-dockerfile-2"}},
            {"build": {"context": cwd, "dockerfile": "test-dockerfile-2"}},
        ),
        (
            {"build": "/workspace/absolute"},
            {"build": {"dockerfile": "test-dockerfile"}},
            {"build": {"context": "/workspace/absolute", "dockerfile": "test-dockerfile"}},
        ),
        (
            {"build": {"dockerfile": "test-dockerfile"}},
            {"build": "/workspace/absolute"},
            {"build": {"context": "/workspace/absolute", "dockerfile": "test-dockerfile"}},
        ),
        (
            {"build": {"dockerfile": "./test-dockerfile-1"}},
            {"build": {"dockerfile": "./test-dockerfile-2", "args": ["ENV1=1"]}},
            {
                "build": {
                    "context": cwd,
                    "dockerfile": "./test-dockerfile-2",
                    "args": ["ENV1=1"],
                }
            },
        ),
        (
            {"build": {"dockerfile": "./test-dockerfile-1", "args": ["ENV1=1"]}},
            {"build": {"dockerfile": "./test-dockerfile-2"}},
            {
                "build": {
                    "context": cwd,
                    "dockerfile": "./test-dockerfile-2",
                    "args": ["ENV1=1"],
                }
            },
        ),
        (
            {"build": {"dockerfile": "./test-dockerfile-1", "args": ["ENV1=1"]}},
            {"build": {"dockerfile": "./test-dockerfile-2", "args": ["ENV2=2"]}},
            {
                "build": {
                    "context": cwd,
                    "dockerfile": "./test-dockerfile-2",
                    "args": ["ENV1=1", "ENV2=2"],
                }
            },
        ),
    ])
    def test_parse_when_multiple_composes(self, input, override, expected):
        compose_test_1 = {"services": {"test-service": input}}
        compose_test_2 = {"services": {"test-service": override}}
        dump_yaml(compose_test_1, "test-compose-1.yaml")
        dump_yaml(compose_test_2, "test-compose-2.yaml")

        podman_compose = PodmanCompose()
        set_args(
            podman_compose,
            ["test-compose-1.yaml", "test-compose-2.yaml"],
            no_normalize=None,
        )

        podman_compose._parse_compose_file()

        actual_compose = {}
        if podman_compose.services:
            podman_compose.services["test-service"].pop("_deps")
            actual_compose = podman_compose.services["test-service"]
        self.assertEqual(actual_compose, expected)


def set_args(podman_compose: PodmanCompose, file_names: list[str], no_normalize: bool) -> None:
    podman_compose.global_args = argparse.Namespace()
    podman_compose.global_args.file = file_names
    podman_compose.global_args.project_name = None
    podman_compose.global_args.env_file = None
    podman_compose.global_args.profile = []
    podman_compose.global_args.in_pod_bool = True
    podman_compose.global_args.no_normalize = no_normalize


def dump_yaml(compose: dict, name: str) -> None:
    # Path(Path.cwd()/"subdirectory").mkdir(parents=True, exist_ok=True)
    with open(name, "w", encoding="utf-8") as outfile:
        yaml.safe_dump(compose, outfile, default_flow_style=False)


def test_clean_test_yamls() -> None:
    test_files = ["test-compose-1.yaml", "test-compose-2.yaml", "test-compose.yaml"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
