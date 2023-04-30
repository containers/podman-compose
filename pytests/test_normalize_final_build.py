# pylint: disable=protected-access

import argparse
import copy
import os
from pathlib import Path
import yaml
from podman_compose import (
    normalize_service,
    normalize,
    normalize_final,
    normalize_service_final,
    PodmanCompose,
)


test_cases_simple_normalization = [
    ({"image": "test-image"}, {"image": "test-image"}),
    (
        {"build": "."},
        {
            "build": {"context": str(Path.cwd()), "dockerfile": "Dockerfile"},
        },
    ),
    (
        {"build": "../relative"},
        {
            "build": {
                "context": str((Path.cwd() / "../relative").resolve()),
                "dockerfile": "Dockerfile",
            },
        },
    ),
    (
        {"build": "./relative"},
        {
            "build": {
                "context": str((Path.cwd() / "./relative").resolve()),
                "dockerfile": "Dockerfile",
            },
        },
    ),
    (
        {"build": "/workspace/absolute"},
        {
            "build": {
                "context": "/workspace/absolute",
                "dockerfile": "Dockerfile",
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
                "context": str(Path.cwd()),
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
                "context": str(Path.cwd()),
                "dockerfile": "Dockerfile",
            },
        },
    ),
    (
        {
            "build": {"context": "../", "dockerfile": "test-dockerfile"},
        },
        {
            "build": {
                "context": str((Path.cwd() / "../").resolve()),
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
                "context": str(Path.cwd()),
                "dockerfile": "./dev/test-dockerfile",
            },
        },
    ),
]


#
# [service.build] is not normalised before coompose files are merged
#
def test_pre_merge_normalize_service_does_not_affect_build_section() -> None:
    for test_input, _ in copy.deepcopy(test_cases_simple_normalization):
        expected_service = copy.deepcopy(test_input)
        actual_service = normalize_service(test_input)
        assert expected_service == actual_service


def test_pre_merge_normalize_does_not_affect_build_section() -> None:
    for test_input, _ in copy.deepcopy(test_cases_simple_normalization):
        expected_result = copy.deepcopy(test_input)
        compose_test = {"services": {"test-service": test_input}}
        compose_expected = {"services": {"test-service": expected_result}}
        actual_compose = normalize(compose_test)
        assert compose_expected == actual_compose


#
# [service.build] is normalised after merges
#
def test_normalize_service_final_returns_absolute_path_in_context() -> None:
    project_dir = str(Path.cwd().resolve())
    for test_input, expected_service in copy.deepcopy(test_cases_simple_normalization):
        actual_service = normalize_service_final(test_input, project_dir)
        assert expected_service == actual_service


def test_normalize_returns_absolute_path_in_context() -> None:
    project_dir = str(Path.cwd().resolve())
    for test_input, expected_result in copy.deepcopy(test_cases_simple_normalization):
        compose_test = {"services": {"test-service": test_input}}
        compose_expected = {"services": {"test-service": expected_result}}
        actual_compose = normalize_final(compose_test, project_dir)
        assert compose_expected == actual_compose


#
# running full parse over single compose files
#
def test__parse_compose_file_when_single_compose() -> None:
    for test_input, expected_result in copy.deepcopy(test_cases_simple_normalization):
        compose_test = {"services": {"test-service": test_input}}
        dump_yaml(compose_test, "test-compose.yaml")

        podman_compose = PodmanCompose()
        set_args(podman_compose, ["test-compose.yaml"])

        podman_compose._parse_compose_file()

        actual_compose = {}
        if podman_compose.services:
            podman_compose.services["test-service"].pop("_deps")
            actual_compose = podman_compose.services["test-service"]
        if actual_compose != expected_result:
            print("compose:   ", test_input)
            print("result:    ", expected_result)

        assert expected_result == actual_compose


test_cases_with_merges = [
    (
        {},
        {"build": "."},
        {"build": {"context": str(Path.cwd()), "dockerfile": "Dockerfile"}},
    ),
    (
        {"build": "."},
        {},
        {"build": {"context": str(Path.cwd()), "dockerfile": "Dockerfile"}},
    ),
    (
        {"build": "/workspace/absolute"},
        {"build": "./relative"},
        {
            "build": {
                "context": str((Path.cwd() / "./relative").resolve()),
                "dockerfile": "Dockerfile",
            }
        },
    ),
    (
        {"build": "./relative"},
        {"build": "/workspace/absolute"},
        {"build": {"context": "/workspace/absolute", "dockerfile": "Dockerfile"}},
    ),
    (
        {"build": "./relative"},
        {"build": "/workspace/absolute"},
        {"build": {"context": "/workspace/absolute", "dockerfile": "Dockerfile"}},
    ),
    (
        {"build": {"dockerfile": "test-dockerfile"}},
        {},
        {"build": {"context": str(Path.cwd()), "dockerfile": "test-dockerfile"}},
    ),
    (
        {},
        {"build": {"dockerfile": "test-dockerfile"}},
        {"build": {"context": str(Path.cwd()), "dockerfile": "test-dockerfile"}},
    ),
    (
        {},
        {"build": {"dockerfile": "test-dockerfile"}},
        {"build": {"context": str(Path.cwd()), "dockerfile": "test-dockerfile"}},
    ),
    (
        {"build": {"dockerfile": "test-dockerfile-1"}},
        {"build": {"dockerfile": "test-dockerfile-2"}},
        {"build": {"context": str(Path.cwd()), "dockerfile": "test-dockerfile-2"}},
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
]


#
# running full parse over merged and extended compose files
#
def test__parse_compose_file_when_multiple_composes() -> None:
    for test_input, test_override, expected_result in copy.deepcopy(
        test_cases_with_merges
    ):
        compose_test_1 = {"services": {"test-service": test_input}}
        compose_test_2 = {"services": {"test-service": test_override}}
        dump_yaml(compose_test_1, "test-compose-1.yaml")
        dump_yaml(compose_test_2, "test-compose-2.yaml")

        podman_compose = PodmanCompose()
        set_args(podman_compose, ["test-compose-1.yaml", "test-compose-2.yaml"])

        podman_compose._parse_compose_file()

        actual_compose = {}
        if podman_compose.services:
            podman_compose.services["test-service"].pop("_deps")
            actual_compose = podman_compose.services["test-service"]
        if actual_compose != expected_result:
            print("compose:   ", test_input)
            print("override:  ", test_override)
            print("result:    ", expected_result)
        compose_expected = expected_result

        assert compose_expected == actual_compose


def set_args(podman_compose: PodmanCompose, file_names: list[str]) -> None:
    podman_compose.global_args = argparse.Namespace()
    podman_compose.global_args.file = file_names
    podman_compose.global_args.project_name = None
    podman_compose.global_args.env_file = None
    podman_compose.global_args.profile = []
    podman_compose.global_args.in_pod = True


def dump_yaml(compose: dict, name: str) -> None:
    # Path(Path.cwd()/"subdirectory").mkdir(parents=True, exist_ok=True)
    with open(name, "w", encoding="utf-8") as outfile:
        yaml.safe_dump(compose, outfile, default_flow_style=False)


def test_clean_test_yamls() -> None:
    test_files = ["test-compose-1.yaml", "test-compose-2.yaml", "test-compose.yaml"]
    for file in test_files:
        if Path(file).exists():
            os.remove(file)
