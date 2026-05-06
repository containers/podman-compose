"""Test that when both build: and image: are specified, the built image
is preferred over the registry image. See: #1445"""

import unittest
from argparse import Namespace
from unittest import mock

from podman_compose import build_one


class TestPreferBuiltImageOverRegistry(unittest.IsolatedAsyncioTestCase):
    @mock.patch("podman_compose.container_to_build_args", return_value=["build-args"])
    @mock.patch("podman_compose.PodmanCompose")
    async def test_build_updates_image_to_localhost(
        self, compose_mock, build_args_mock
    ):
        """When build: and image: are both set and image has no registry prefix,
        build_one should update cnt['image'] to localhost/<image> so the locally
        built image is used instead of the registry one."""
        compose_mock.podman.run = mock.AsyncMock(return_value=0)

        cnt = {"build": {"context": "."}, "image": "caddy:alpine"}
        args = Namespace(if_not_exists=None)

        result = await build_one(compose_mock, args, cnt)

        assert result == 0
        assert cnt["image"] == "localhost/caddy:alpine"

    @mock.patch("podman_compose.container_to_build_args", return_value=["build-args"])
    @mock.patch("podman_compose.PodmanCompose")
    async def test_build_does_not_double_prefix_localhost(
        self, compose_mock, build_args_mock
    ):
        """If image already starts with localhost/, don't double-prefix."""
        compose_mock.podman.run = mock.AsyncMock(return_value=0)

        cnt = {"build": {"context": "."}, "image": "localhost/caddy:alpine"}
        args = Namespace(if_not_exists=None)

        result = await build_one(compose_mock, args, cnt)

        assert result == 0
        assert cnt["image"] == "localhost/caddy:alpine"

    @mock.patch("podman_compose.container_to_build_args", return_value=["build-args"])
    @mock.patch("podman_compose.PodmanCompose")
    async def test_build_does_not_prefix_registry_image(
        self, compose_mock, build_args_mock
    ):
        """If image has a registry prefix (contains /), don't add localhost/."""
        compose_mock.podman.run = mock.AsyncMock(return_value=0)

        cnt = {"build": {"context": "."}, "image": "ghcr.io/user/caddy:alpine"}
        args = Namespace(if_not_exists=None)

        result = await build_one(compose_mock, args, cnt)

        assert result == 0
        assert cnt["image"] == "ghcr.io/user/caddy:alpine"

    @mock.patch("podman_compose.container_to_build_args", return_value=["build-args"])
    @mock.patch("podman_compose.PodmanCompose")
    async def test_build_failure_does_not_update_image(
        self, compose_mock, build_args_mock
    ):
        """If the build fails, don't update the image name."""
        compose_mock.podman.run = mock.AsyncMock(return_value=1)

        cnt = {"build": {"context": "."}, "image": "caddy:alpine"}
        args = Namespace(if_not_exists=None)

        result = await build_one(compose_mock, args, cnt)

        assert result == 1
        assert cnt["image"] == "caddy:alpine"
