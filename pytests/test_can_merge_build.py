import copy
import os
import argparse
import yaml
from podman_compose import normalize_service, PodmanCompose


test_cases_simple = [
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
]


def test_normalize_service_simple():
    for test_case, expected in copy.deepcopy(test_cases_simple):
        test_original = copy.deepcopy(test_case)
        test_case = normalize_service(test_case)
        test_result = expected == test_case
        if not test_result:
            print("test:     ", test_original)
            print("expected: ", expected)
            print("actual:   ", test_case)
        assert test_result


test_cases_sub_dir = [
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
]


def test_normalize_service_with_sub_dir():
    for test_case, expected in copy.deepcopy(test_cases_sub_dir):
        test_original = copy.deepcopy(test_case)
        test_case = normalize_service(test_case, sub_dir="./sub_dir")
        test_result = expected == test_case
        if not test_result:
            print("test:     ", test_original)
            print("expected: ", expected)
            print("actual:   ", test_case)
        assert test_result


test_cases_merges = [
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
]


def test__parse_compose_file_when_multiple_composes() -> None:
    for test_input, test_override, expected_result in copy.deepcopy(test_cases_merges):
        compose_test_1 = {"services": {"test-service": test_input}}
        compose_test_2 = {"services": {"test-service": test_override}}
        dump_yaml(compose_test_1, "test-compose-1.yaml")
        dump_yaml(compose_test_2, "test-compose-2.yaml")

        podman_compose = PodmanCompose()
        set_args(podman_compose, ["test-compose-1.yaml", "test-compose-2.yaml"])

        podman_compose._parse_compose_file()  # pylint: disable=protected-access

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
    with open(name, "w", encoding="utf-8") as outfile:
        yaml.safe_dump(compose, outfile, default_flow_style=False)


def test_clean_test_yamls() -> None:
    test_files = ["test-compose-1.yaml", "test-compose-2.yaml"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
