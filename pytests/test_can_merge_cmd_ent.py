import copy
import os
import argparse
import yaml
import unittest
from parameterized import parameterized
from podman_compose import normalize_service, PodmanCompose

test_keys = ["command", "entrypoint"]


class TestMergeBuild(unittest.TestCase):
    @parameterized.expand([
        ({"$$$": []}, {"$$$": []}),
        ({"$$$": ["sh"]}, {"$$$": ["sh"]}),
        ({"$$$": ["sh", "-c", "date"]}, {"$$$": ["sh", "-c", "date"]}),
        ({"$$$": "sh"}, {"$$$": ["sh"]}),
        ({"$$$": "sleep infinity"}, {"$$$": ["sleep", "infinity"]}),
        (
            {"$$$": "bash -c 'sleep infinity'"},
            {"$$$": ["bash", "-c", "sleep infinity"]},
        ),
    ])
    def test_normalize_service(self, input_template, expected_template):
        for key in test_keys:
            test_input, _, expected = template_to_expression(
                input_template, {}, expected_template, key
            )
            self.assertEqual(normalize_service(test_input), expected)

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
    def test_parse_compose_file_when_multiple_composes(
        self, base_template, override_template, expected_template
    ):
        for key in test_keys:
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


def set_args(podman_compose: PodmanCompose, file_names: list[str]) -> None:
    podman_compose.global_args = argparse.Namespace()
    podman_compose.global_args.file = file_names
    podman_compose.global_args.project_name = None
    podman_compose.global_args.env_file = None
    podman_compose.global_args.profile = []
    podman_compose.global_args.in_pod = True
    podman_compose.global_args.no_normalize = None


def dump_yaml(compose: dict, name: str) -> None:
    with open(name, "w", encoding="utf-8") as outfile:
        yaml.safe_dump(compose, outfile, default_flow_style=False)


def test_clean_test_yamls() -> None:
    test_files = ["test-compose-1.yaml", "test-compose-2.yaml"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
