# SPDX-License-Identifier: GPL-2.0

import argparse
import asyncio
import unittest
from unittest import mock

from podman_compose import Podman
from podman_compose import PodmanCompose


class TestPodmanBuildArgsOrder(unittest.IsolatedAsyncioTestCase):
    async def test_podman_build_args_come_after_compose_options(self) -> None:
        compose = PodmanCompose()
        compose.global_args = argparse.Namespace(
            podman_args=[], podman_build_args=["--build-arg CUSTOM_VAR=1"]
        )
        podman = Podman(compose, "podman", False, asyncio.Semaphore(1))

        with mock.patch("asyncio.create_subprocess_exec") as create:
            create.return_value.wait = mock.AsyncMock(return_value=0)
            create.return_value.stdout = None
            create.return_value.stderr = None
            create.return_value.returncode = 0
            try:
                await podman.run([], "build", ["--build-arg", "CUSTOM_VAR=0", "."])
            except Exception:  # pylint: disable=broad-except
                pass

        argv = list(create.call_args.args)
        self.assertEqual(
            argv,
            [
                "podman",
                "build",
                "--build-arg",
                "CUSTOM_VAR=0",
                "--build-arg",
                "CUSTOM_VAR=1",
                ".",
            ],
        )
