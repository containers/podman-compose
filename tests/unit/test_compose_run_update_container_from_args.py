# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import tempfile
import unittest

from podman_compose import PodmanCompose
from podman_compose import compose_run_update_container_from_args


class TestComposeRunUpdateContainerFromArgs(unittest.TestCase):
    def test_minimal(self) -> None:
        cnt = get_minimal_container()
        compose = get_minimal_compose()
        args = get_minimal_args()

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {"name": "default_name", "tty": True}
        self.assertEqual(cnt, expected_cnt)

    def test_additional_env_value_equals(self) -> None:
        cnt = get_minimal_container()
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.env = ["key=valuepart1=valuepart2"]

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {
            "environment": {
                "key": "valuepart1=valuepart2",
            },
            "name": "default_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_publish_ports(self) -> None:
        cnt = get_minimal_container()
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.publish = ["1111", "2222:2222"]

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {
            "name": "default_name",
            "ports": ["1111", "2222:2222"],
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_container_name_from_compose(self) -> None:
        cnt = {"container_name": "compose_custom_name"}
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.name = None

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {
            "container_name": "compose_custom_name",
            "name": "compose_custom_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_cli_name_overrides_container_name(self) -> None:
        cnt = {"container_name": "compose_custom_name"}
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.name = "cli_override_name"

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {
            "container_name": "compose_custom_name",
            "name": "cli_override_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_fallback_to_generated_name(self) -> None:
        cnt = get_minimal_container()
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.name = None

        compose_run_update_container_from_args(compose, cnt, args)

        self.assertTrue(cnt["name"].startswith("test_project_test_service_tmp"))
        self.assertEqual(cnt["tty"], True)

    def test_env_from_file(self) -> None:
        cnt = get_minimal_container()
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.env_from_file = [get_env_file_path("project-1.env")]

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {
            "environment": {
                "ZZVAR1": "podman-rocks-123",
                "ZZVAR2": "podman-rocks-124",
                "ZZVAR3": "podman-rocks-125",
            },
            "name": "default_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_env_from_file_multiple_first_file_wins(self) -> None:
        cnt = get_minimal_container()
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.env_from_file = [
            get_env_file_path("project-2.env"),
            get_env_file_path("project-1.env"),
        ]

        compose_run_update_container_from_args(compose, cnt, args)

        # Same as docker compose: a variable set by an earlier file is not overridden by a
        # later one, variables that only a later file sets are added.
        expected_cnt = {
            "environment": {
                "ZZVAR1": "podman-rocks-223",
                "ZZVAR2": "podman-rocks-224",
                "ZZVAR3": "podman-rocks-125",
            },
            "name": "default_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_env_overrides_env_from_file(self) -> None:
        cnt = get_minimal_container()
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.env = ["ZZVAR1=from-cli"]
        args.env_from_file = [get_env_file_path("project-1.env")]

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {
            "environment": {
                "ZZVAR1": "from-cli",
                "ZZVAR2": "podman-rocks-124",
                "ZZVAR3": "podman-rocks-125",
            },
            "name": "default_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_env_from_file_overrides_service_environment(self) -> None:
        cnt = {"environment": {"ZZVAR1": "from-service", "OTHER": "kept"}}
        compose = get_minimal_compose()
        args = get_minimal_args()
        args.env_from_file = [get_env_file_path("project-2.env")]

        compose_run_update_container_from_args(compose, cnt, args)

        expected_cnt = {
            "environment": {
                "ZZVAR1": "podman-rocks-223",
                "ZZVAR2": "podman-rocks-224",
                "OTHER": "kept",
            },
            "name": "default_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)

    def test_env_from_file_ignores_bare_keys(self) -> None:
        cnt = {"environment": {"OTHER": "from-service"}}
        compose = get_minimal_compose()
        args = get_minimal_args()
        with tempfile.TemporaryDirectory() as tmp_dir:
            bare_keys_path = os.path.join(tmp_dir, "bare-keys.env")
            with open(bare_keys_path, "w", encoding="utf-8") as f:
                f.write("OTHER\nZZVAR1\n")
            args.env_from_file = [bare_keys_path, get_env_file_path("project-2.env")]

            compose_run_update_container_from_args(compose, cnt, args)

        # Same as docker compose: a line without a value neither replaces the service's value
        # nor stops a later file from setting the variable.
        expected_cnt = {
            "environment": {
                "OTHER": "from-service",
                "ZZVAR1": "podman-rocks-223",
                "ZZVAR2": "podman-rocks-224",
            },
            "name": "default_name",
            "tty": True,
        }
        self.assertEqual(cnt, expected_cnt)


def get_env_file_path(name: str) -> str:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.realpath(
        os.path.join(repo_root, "tests/integration/env_file_tests/env-files", name)
    )


def get_minimal_container() -> dict:
    return {}


def get_minimal_compose() -> PodmanCompose:
    compose = PodmanCompose()
    compose.project_name = "test_project"
    return compose


def get_minimal_args() -> argparse.Namespace:
    return argparse.Namespace(
        T=None,
        cnt_command=None,
        entrypoint=None,
        env=None,
        env_from_file=None,
        name="default_name",
        rm=None,
        service="test_service",
        publish=None,
        service_ports=None,
        user=None,
        volume=None,
        workdir=None,
    )
