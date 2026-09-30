# SPDX-License-Identifier: GPL-2.0
import asyncio
import subprocess
from unittest import IsolatedAsyncioTestCase
from unittest import mock

from podman_compose import Podman
from podman_compose import PodmanCompose
from podman_compose import assert_cnt_nets
from podman_compose import assert_volume


def get_dry_run_compose() -> mock.MagicMock:
    compose = mock.MagicMock(spec=PodmanCompose)
    compose.project_name = "test_project"
    compose.get_podman_args.return_value = []
    compose.podman = Podman(compose, "podman", True, asyncio.Semaphore(1))
    return compose


class TestDryRun(IsolatedAsyncioTestCase):
    async def test_assert_volume_does_not_create_volume(self) -> None:
        compose = get_dry_run_compose()
        mount_dict = {
            "type": "volume",
            "source": "testvol",
            "target": "/root",
            "_vol": {"name": "test_project_testvol"},
        }

        with mock.patch.object(compose.podman, "output") as output:
            output.side_effect = [
                subprocess.CalledProcessError(1, "podman volume inspect"),
                b"",
                b"",
            ]
            await assert_volume(compose, mount_dict)

        self.assertEqual(
            [args for args, _ in output.call_args_list],
            [([], "volume", ["inspect", "test_project_testvol"])],
        )

    async def test_assert_cnt_nets_does_not_create_network(self) -> None:
        compose = get_dry_run_compose()
        compose.networks = {"srv": {}}
        compose.default_net = "srv"
        cnt = {"service_name": "alpine", "networks": ["srv"]}

        with mock.patch.object(compose.podman, "output") as output:
            output.side_effect = [
                subprocess.CalledProcessError(1, "podman network exists"),
                b"",
                b"",
            ]
            with mock.patch(
                "podman_compose.default_network_name_for_project",
                return_value="test_project_srv",
            ):
                await assert_cnt_nets(compose, cnt)

        self.assertEqual(
            [args for args, _ in output.call_args_list],
            [([], "network", ["exists", "test_project_srv"])],
        )
