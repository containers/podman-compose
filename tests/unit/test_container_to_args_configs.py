# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import unittest
from typing import cast
from unittest import mock
from unittest.mock import call

from parameterized import parameterized

from podman_compose import PodmanCompose
from podman_compose import PodmanComposeError
from podman_compose import container_to_args
from tests.unit.test_container_to_args import create_compose_mock as super_compose_mock
from tests.unit.test_container_to_args import get_minimal_container as super_minimal_container


def create_compose_mock(project_name: str = "test_project_name") -> PodmanCompose:
    compose = cast(mock.Mock, super_compose_mock(project_name))

    artifact_store = {
        "my_external_config": "sha256:EXTERNAL_IS_NOT_CHECKED",
    }

    async def podman_output(
        podman_args: list[str], cmd: str = "", cmd_args: list[str] | None = None
    ) -> bytes:
        if cmd == "artifact":
            assert type(cmd_args) is list and len(cmd_args) >= 2, (
                "invalid number of arguments provided to podman artifact"
            )
            artifact_op = cmd_args[0]
            if artifact_op == "add":
                artifact_name = cmd_args[-2]
                with open(cmd_args[-1], 'rb') as artifact_file:
                    artifact_hash = hashlib.sha256(artifact_file.read())
                artifact_store[artifact_name] = f'sha256:{artifact_hash.hexdigest()}'
            elif artifact_op == "inspect":
                artifact_name = cmd_args[-1]
                if artifact_name not in artifact_store:
                    raise subprocess.CalledProcessError(
                        125,
                        ["podman"] + podman_args + [cmd] + cmd_args,
                        f'Error: {artifact_name}: artifact does not exist'.encode(),
                    )
                inspect_result = {
                    "Manifest": {
                        "layers": [
                            {
                                "digest": artifact_store[artifact_name],
                                "annotations": {
                                    "io.podman.compose.project": project_name,
                                    "com.docker.compose.project": project_name,
                                },
                            }
                        ],
                    },
                    "Name": artifact_name,
                }
                return json.dumps(inspect_result, indent=4).encode()

        return b''

    compose.podman.output = mock.Mock(side_effect=podman_output)

    return compose


def get_minimal_container(service_name: str = "test-service") -> dict:
    cnt = super_minimal_container()
    cnt["_service"] = service_name
    return cnt


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def artifact_qualified_name(project_name: str | None, artifact_name: str) -> str:
    return f"localhost/podman-compose/{project_name}_config_{artifact_name}:latest"


def artifact_add_args(project_name: str | None, artifact_name: str) -> list:
    return [
        "add",
        "--replace",
        "--file-type",
        "application/octet-stream",
        "--annotation",
        f"io.podman.compose.project={project_name}",
        "--annotation",
        f"com.docker.compose.project={project_name}",
        artifact_qualified_name(project_name, artifact_name),
        mock.ANY,  # tempfile path
    ]


class TestContainerToArgsConfigs(unittest.IsolatedAsyncioTestCase):
    @parameterized.expand([
        (
            "config_no_name",
            {"my_config": "my_external_config", "external": True},
            {},  # must have a name
        ),
        (
            "no_config_name_in_declared_configs",
            {},  # must have a name
            {
                "source": "my_external_config",
            },
        ),
        (
            "config_name_does_not_match_declared_configs_name",
            {
                "wrong_name": "my_config_name",
            },
            {
                "source": "name",  # config name must match the one in declared_configs
            },
        ),
        (
            "config_name_empty_string",
            {"": "my_config_name"},
            {
                "source": "",  # can not be empty string
            },
        ),
    ])
    async def test_config_name(
        self, test_name: str, declared_configs: dict, add_to_minimal_container: dict
    ) -> None:
        c = create_compose_mock()
        c.declared_configs = declared_configs

        cnt = get_minimal_container()
        cnt["configs"] = [add_to_minimal_container]

        with self.assertRaises(ValueError) as context:
            await container_to_args(c, cnt)
        self.assertIn('ERROR: undeclared config: ', str(context.exception))

    async def test_config_string_no_external_name_in_declared_configs(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {"my_external_config": {"external": True}}
        cnt = get_minimal_container()
        cnt["configs"] = [
            "my_external_config",
        ]
        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--mount",
                "type=artifact,source=my_external_config,target=/my_external_config",
                "busybox",
            ],
        )

    async def test_config_string_options_external_name_in_declared_configs(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "my_config_name": {
                "external": True,
                "name": "my_external_config",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "my_config_name",
                "target": "/my_config_name",
            }
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--mount",
                "type=artifact,source=my_external_config,target=/my_config_name",
                "busybox",
            ],
        )

    async def test_config_string_external_name_in_declared_configs_does_not_match_config(
        self,
    ) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "my_config_name": {
                "external": True,
                "name": "wrong_config_name",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            "my_config_name",
        ]

        with self.assertRaises(PodmanComposeError) as context:
            await container_to_args(c, cnt)
        self.assertIn('External config [wrong_config_name] does not exist.', str(context.exception))

    async def test_config_target_does_not_match_config_name(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "my_external_config": {
                "external": True,
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "my_external_config",
                "target": "/tmp/custom_path",
            }
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--mount",
                "type=artifact,source=my_external_config,target=/tmp/custom_path",
                "busybox",
            ],
        )

    @parameterized.expand([
        (
            "no_config_target",
            {
                "file_config": {
                    "file": "./my_config",
                }
            },
            "file_config",
            repo_root() + "/test_dirname/my_config:/file_config:ro,rprivate,rbind",
        ),
        (
            "relabel",
            {"file_config": {"file": "./my_config", "x-podman.relabel": "Z"}},
            "file_config",
            repo_root() + "/test_dirname/my_config:/file_config:ro,rprivate,rbind,Z",
        ),
        (
            "relabel",
            {"file_config": {"file": "./my_config", "x-podman.relabel": "z"}},
            "file_config",
            repo_root() + "/test_dirname/my_config:/file_config:ro,rprivate,rbind,z",
        ),
        (
            "custom_target_name",
            {
                "file_config": {
                    "file": "./my_config",
                }
            },
            {
                "source": "file_config",
                "target": "/etc/custom_name",
            },
            repo_root() + "/test_dirname/my_config:/etc/custom_name:ro,rprivate,rbind",
        ),
        (
            "no_custom_target_name",
            {
                "file_config": {
                    "file": "./my_config",
                }
            },
            {
                "source": "file_config",
            },
            repo_root() + "/test_dirname/my_config:/file_config:ro,rprivate,rbind",
        ),
        (
            "custom_location",
            {
                "file_config": {
                    "file": "./my_config",
                }
            },
            {
                "source": "file_config",
                "target": "/etc/custom_location",
            },
            repo_root() + "/test_dirname/my_config:/etc/custom_location:ro,rprivate,rbind",
        ),
    ])
    async def test_file_config(
        self,
        test_name: str,
        declared_configs: dict,
        add_to_minimal_container: dict,
        expected_volume_ref: str,
    ) -> None:
        c = create_compose_mock()
        c.declared_configs = declared_configs
        cnt = get_minimal_container()
        cnt["configs"] = [add_to_minimal_container]
        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--volume",
                expected_volume_ref,
                "busybox",
            ],
        )

    async def test_file_config_unused_params_warning(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "file_config": {
                "file": "./my_config",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "file_config",
                "target": "/unused_params_warning",
                "uid": "103",
                "gid": "103",
                "mode": "400",
            }
        ]
        with self.assertLogs() as cm:
            args = await container_to_args(c, cnt)
        self.assertEqual(len(cm.output), 1)
        self.assertIn('with uid, gid, or mode.', cm.output[0])
        self.assertIn('unused_params_warning', cm.output[0])

        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--volume",
                repo_root() + "/test_dirname/my_config:/unused_params_warning:ro,rprivate,rbind",
                "busybox",
            ],
        )

    async def test_content_config(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "content_config": {
                "content": "this-is-the-config-content",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "content_config",
            }
        ]
        args = await container_to_args(c, cnt)

        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--mount",
                "type=artifact,"
                f"source=localhost/podman-compose/{c.project_name}_config_content_config:latest,"
                "target=/content_config",
                "busybox",
            ],
        )

    @mock.patch.dict(os.environb, {b'CONFIG_VAL': b'config-from-environment'})
    async def test_environment_config(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "environment_config": {
                "environment": "CONFIG_VAL",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "environment_config",
            }
        ]
        args = await container_to_args(c, cnt)

        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--mount",
                "type=artifact,"
                f"source=localhost/podman-compose/{c.project_name}_config_environment_config:latest,"
                "target=/environment_config",
                "busybox",
            ],
        )

    async def test_artifact_idempotent_creation(self) -> None:
        c = create_compose_mock()
        output_mock = cast(mock.Mock, c.podman.output)
        c.declared_configs = {
            "content_config": {
                "content": "this-is-the-config-content",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "content_config",
            }
        ]
        cnt2 = get_minimal_container("test-service-2")
        cnt2["configs"] = [
            {
                "source": "content_config",
            }
        ]

        INSPECT_ARTIFACT = call(
            [],
            "artifact",
            ["inspect", artifact_qualified_name(c.project_name, "content_config")],
        )
        ADD_ARTIFACT = call([], "artifact", artifact_add_args(c.project_name, "content_config"))

        await container_to_args(c, cnt)
        output_mock.assert_has_calls([
            # Doesn't exist yet
            INSPECT_ARTIFACT,
            # Created
            ADD_ARTIFACT,
            # Validated after creation
            INSPECT_ARTIFACT,
        ])

        output_mock.reset_mock()
        await container_to_args(c, cnt2)
        # Existence checked when second service references it
        output_mock.assert_called_once_with(*INSPECT_ARTIFACT.args)

    async def test_artifact_recreate_on_change(self) -> None:
        c = create_compose_mock()
        output_mock = cast(mock.Mock, c.podman.output)
        c.declared_configs = {
            "content_config": {
                "content": "this-is-the-config-content",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "content_config",
            }
        ]

        INSPECT_ARTIFACT = call(
            [],
            "artifact",
            ["inspect", artifact_qualified_name(c.project_name, "content_config")],
        )
        ADD_ARTIFACT = call([], "artifact", artifact_add_args(c.project_name, "content_config"))

        await container_to_args(c, cnt)
        output_mock.assert_has_calls([
            # Doesn't exist yet
            INSPECT_ARTIFACT,
            # Created
            ADD_ARTIFACT,
            # Validated after creation
            INSPECT_ARTIFACT,
        ])

        output_mock.reset_mock()
        await container_to_args(c, cnt)
        # Validate that it is not re-created if the content does not change
        output_mock.assert_called_once_with(*INSPECT_ARTIFACT.args)

        # Modify the content, then call container_to_args again, as if podman compose up were run
        # a second time
        c.declared_configs = {
            "content_config": {
                "content": "this-is-CHANGED-config-content",
            }
        }

        output_mock.reset_mock()
        await container_to_args(c, cnt)
        output_mock.assert_has_calls([
            # Exists and metadata retrieved
            INSPECT_ARTIFACT,
            # Re-created because hash doesn't match
            ADD_ARTIFACT,
            # Validated after creation
            INSPECT_ARTIFACT,
        ])
