# SPDX-License-Identifier: GPL-2.0

import unittest
from unittest import mock
from podman_compose import container_to_args


def create_compose_mock():
    compose = mock.Mock()
    compose.project_name = "test_project_name"
    compose.dirname = "test_dirname"
    compose.container_names_by_service.get = mock.Mock(return_value=None)
    compose.prefer_volume_over_mount = False
    compose.default_net = None
    compose.networks = {}
    return compose


def get_minimal_container():
    return {
        "name": "project_name_service_name1",
        "service_name": "service_name",
        "image": "busybox",
    }


class TestContainerToArgs(unittest.TestCase):
    async def test_minimal(self):
        c = create_compose_mock()

        cnt = get_minimal_container()

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--net",
                "",
                "--network-alias",
                "service_name",
                "busybox",
            ],
        )

    async def test_runtime(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["runtime"] = "runsc"

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--net",
                "",
                "--network-alias",
                "service_name",
                "--runtime",
                "runsc",
                "busybox",
            ],
        )
