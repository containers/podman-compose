# SPDX-License-Identifier: GPL-2.0

from __future__ import annotations

import argparse
import unittest
from typing import Any
from typing import Callable
from unittest import mock

from podman_compose import compose_kill
from podman_compose import compose_pause
from podman_compose import compose_ps
from podman_compose import compose_restart
from podman_compose import compose_start
from podman_compose import compose_stop
from podman_compose import compose_unpause


def get_compose(run_results: list[int | None]) -> Any:
    compose = mock.Mock()
    compose.container_names_by_service = {"web": ["p_web_1"], "db": ["p_db_1"]}
    compose.container_by_name = {"p_web_1": {}, "p_db_1": {}}
    compose.project_name = "p"
    compose.assert_services = mock.Mock()
    compose.podman.run = mock.AsyncMock(side_effect=run_results)
    return compose


def get_args() -> argparse.Namespace:
    return argparse.Namespace(
        services=[],
        timeout=1,
        wait=False,
        quiet=False,
        format=None,
        all=True,
        signal=None,
    )


class TestCommandExitCodes(unittest.IsolatedAsyncioTestCase):
    async def test_podman_exit_code_is_returned(self) -> None:
        cases: list[tuple[str, Callable, list[int | None], int]] = [
            ("start", compose_start, [0, 125], 125),
            ("stop", compose_stop, [125, 0], 125),
            ("restart", compose_restart, [0, 0], 0),
            ("ps", compose_ps, [125], 125),
            ("pause", compose_pause, [125], 125),
            ("unpause", compose_unpause, [0], 0),
            ("kill", compose_kill, [125], 125),
        ]
        for name, cmd, run_results, expected in cases:
            with self.subTest(command=name):
                compose = get_compose(run_results)
                self.assertEqual(await cmd(compose, get_args()), expected)

    async def test_dry_run_is_success(self) -> None:
        # Podman.run() returns None in --dry-run mode
        compose = get_compose([None, None])
        self.assertEqual(await compose_stop(compose, get_args()), 0)
