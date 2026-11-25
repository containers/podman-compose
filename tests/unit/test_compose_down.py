# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import unittest
from typing import Any
from typing import cast
from unittest import mock
from unittest.mock import call

from podman_compose import PodmanCompose
from podman_compose import compose_down
from tests.unit.test_container_to_args_configs import artifact_qualified_name


def create_compose_mock(project_name: str = "test_project_name") -> PodmanCompose:
    compose = mock.Mock()
    compose.project_name = project_name
    compose.services = {}
    type(compose).containers = mock.PropertyMock(
        side_effect=lambda: [v | {"_service": k} for k, v in compose.services.items()]
    )
    compose.pods = []
    # compose.dirname = "test_dirname"
    # compose.container_names_by_service.get = mock.Mock(return_value=None)
    # compose.join_name_parts = mock.Mock(side_effect=lambda *args: '_'.join(args))
    compose.format_name = mock.Mock(side_effect=lambda *args: '_'.join([project_name, *args]))

    artifact_store = {
        artifact_qualified_name(project_name, "my_config_name"): "sha256:NOT_CHECKED_DURING_REMOVE",
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
                        "annotations": {
                            "io.podman.compose.project": project_name,
                            "com.docker.compose.project": project_name,
                        },
                    },
                    "Name": artifact_name,
                }
                return json.dumps(inspect_result, indent=4).encode()

        return b''

    compose.podman.output = mock.Mock(side_effect=podman_output)
    compose.podman.run = mock.AsyncMock(return_value=0)
    compose.podman.network_ls = mock.AsyncMock(return_value=[])

    return compose


def get_minimal_container(service_name: str = "service_name") -> dict[str, Any]:
    return {
        "name": "project_name_service_name1",
        "service_name": service_name,
        "image": "busybox",
    }


def get_compose_down_empty_args() -> argparse.Namespace:
    args = argparse.Namespace()
    args.volumes = False
    args.remove_orphans = False
    args.rmi = None
    args.timeout = None
    args.services = None

    return args


class TestComposeDown(unittest.IsolatedAsyncioTestCase):
    async def test_removes_config_artifacts(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "my_config_name": {
                "content": "this-is-the-config-content",
            }
        }
        cnt = get_minimal_container()
        cnt["configs"] = [
            {
                "source": "my_config_name",
            }
        ]
        c.services["service_name"] = cnt

        down_args = get_compose_down_empty_args()
        # TODO: self.assertNoLogs, available in Python >= 3.10, would be a useful
        # check here that no warnings are issued when removing artifacts
        await compose_down(c, down_args)

        config_artifact_name = artifact_qualified_name(c.project_name, "my_config_name")
        output_mock = cast(mock.Mock, c.podman.output)
        output_mock.assert_has_calls([
            call(
                [],
                "artifact",
                ["inspect", config_artifact_name],
            ),
            call(
                [],
                "artifact",
                ["rm", config_artifact_name],
            ),
        ])

    async def test_keeps_artifacts_used_by_multiple_services(self) -> None:
        c = create_compose_mock()
        c.declared_configs = {
            "my_config_name": {
                "content": "this-is-the-config-content",
            }
        }
        cnt = get_minimal_container("test-service-1")
        cnt["configs"] = [
            {
                "source": "my_config_name",
            }
        ]
        c.services["test-service-1"] = cnt
        cnt2 = get_minimal_container("test-service-2")
        cnt2["configs"] = [
            {
                "source": "my_config_name",
            }
        ]
        c.services["test-service-2"] = cnt2

        config_artifact_name = artifact_qualified_name(c.project_name, "my_config_name")
        output_mock = cast(mock.Mock, c.podman.output)

        down_args = get_compose_down_empty_args()
        down_args.services = ["test-service-1"]
        await compose_down(c, down_args)
        # No configs to remove, so podman artifact is never called
        output_mock.assert_not_called()

        output_mock.reset_mock()
        down2_args = get_compose_down_empty_args()
        await compose_down(c, down2_args)
        output_mock.assert_called_with([], "artifact", ["rm", config_artifact_name])
