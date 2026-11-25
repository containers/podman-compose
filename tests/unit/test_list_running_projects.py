# SPDX-License-Identifier: GPL-2.0

import argparse
import asyncio
import contextlib
import io
import os
import unittest
from unittest import mock

from podman_compose import Podman
from podman_compose import PodmanCompose
from podman_compose import list_running_projects


class TestListRunningProjects(unittest.IsolatedAsyncioTestCase):
    async def test_json_output_reports_running_and_stopped_containers(self) -> None:
        compose = PodmanCompose()
        compose.global_args = argparse.Namespace(podman_args=[])
        compose.podman = Podman(compose, semaphore=asyncio.Semaphore(1))
        compose.containers = [
            {"name": "example_web_1", "image": "test-image"},
            {"name": "example_worker_1", "image": "test-image"},
        ]
        running = mock.Mock(
            returncode=0,
            communicate=mock.AsyncMock(
                return_value=(b"running\ntrue\nproject\ncompose.yml\n", b"")
            ),
        )
        stopped = mock.Mock(
            returncode=0,
            communicate=mock.AsyncMock(
                return_value=(b"exited\nfalse\nproject\ncompose.yml\n", b"")
            ),
        )
        stdout = io.StringIO()
        with mock.patch("asyncio.create_subprocess_exec", side_effect=[running, stopped]) as create:
            with contextlib.redirect_stdout(stdout):
                await list_running_projects(compose, argparse.Namespace(format="json"))

        self.assertEqual(
            [call.args[:4] for call in create.await_args_list],
            [
                ("podman", "inspect", "example_web_1", "--format"),
                ("podman", "inspect", "example_worker_1", "--format"),
            ],
        )
        self.assertEqual(
            stdout.getvalue(),
            str([
                {
                    "Name": "example_web_1",
                    "Status": "running(1)",
                    "ConfigFiles": os.path.join("project", "compose.yml"),
                },
                {
                    "Name": "example_worker_1",
                    "Status": "exited(0)",
                    "ConfigFiles": os.path.join("project", "compose.yml"),
                },
            ])
            + "\n",
        )
