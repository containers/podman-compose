# SPDX-License-Identifier: GPL-2.0

from __future__ import annotations

import argparse
import subprocess
import unittest
from unittest import mock

from podman_compose import build_one


def create_compose_mock() -> mock.Mock:
    compose = mock.Mock()
    compose.podman.output = mock.AsyncMock(return_value=b"image-id")
    compose.podman.run = mock.AsyncMock(return_value=0)
    return compose


def get_container(pull_policy: str | None = None) -> dict:
    cnt = {
        "name": "project_name_service_name1",
        "service_name": "service_name",
        "image": "new-image",
        "build": {},
    }
    if pull_policy is not None:
        cnt["pull_policy"] = pull_policy
    return cnt


class TestBuildOne(unittest.IsolatedAsyncioTestCase):
    async def test_no_build_section_does_nothing(self) -> None:
        compose = create_compose_mock()
        cnt = get_container()
        del cnt["build"]
        args = argparse.Namespace(if_not_exists=True, pull=None, build_arg=[])

        status = await build_one(compose, args, cnt)

        self.assertIsNone(status)
        compose.podman.run.assert_not_called()

    @mock.patch("podman_compose.container_to_build_args", return_value=[])
    async def test_existing_image_skips_build(self, _container_to_build_args: mock.Mock) -> None:
        compose = create_compose_mock()
        args = argparse.Namespace(if_not_exists=True, pull=None, build_arg=[])

        status = await build_one(compose, args, get_container())

        self.assertIsNone(status)
        compose.podman.run.assert_not_called()

    @mock.patch("podman_compose.container_to_build_args", return_value=[])
    async def test_missing_image_builds(self, _container_to_build_args: mock.Mock) -> None:
        compose = create_compose_mock()
        compose.podman.output.side_effect = subprocess.CalledProcessError(1, "podman inspect")
        args = argparse.Namespace(if_not_exists=True, pull=None, build_arg=[])

        status = await build_one(compose, args, get_container())

        self.assertEqual(status, 0)
        compose.podman.run.assert_awaited_once_with([], "build", [])

    @mock.patch("podman_compose.container_to_build_args", return_value=[])
    async def test_pull_policy_build_rebuilds_existing_image(
        self, _container_to_build_args: mock.Mock
    ) -> None:
        compose = create_compose_mock()
        args = argparse.Namespace(if_not_exists=True, pull=None, build_arg=[])

        status = await build_one(compose, args, get_container(pull_policy="build"))

        self.assertEqual(status, 0)
        compose.podman.run.assert_awaited_once_with([], "build", [])

    @mock.patch("podman_compose.container_to_build_args", return_value=[])
    async def test_cli_pull_never_overrides_pull_policy_build(
        self, _container_to_build_args: mock.Mock
    ) -> None:
        compose = create_compose_mock()
        args = argparse.Namespace(if_not_exists=True, pull="never", build_arg=[])

        status = await build_one(compose, args, get_container(pull_policy="build"))

        self.assertIsNone(status)
        compose.podman.run.assert_not_called()

    @mock.patch("podman_compose.container_to_build_args", return_value=[])
    async def test_cli_pull_build_forces_rebuild(self, _container_to_build_args: mock.Mock) -> None:
        compose = create_compose_mock()
        args = argparse.Namespace(if_not_exists=True, pull="build", build_arg=[])

        status = await build_one(compose, args, get_container())

        self.assertEqual(status, 0)
        compose.podman.run.assert_awaited_once_with([], "build", [])
