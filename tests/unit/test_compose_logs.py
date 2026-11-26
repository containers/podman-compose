# SPDX-License-Identifier: GPL-2.0

import asyncio
import signal
import sys
import unittest
from argparse import Namespace
from unittest import mock

from podman_compose import compose_logs


async def podman_logs_follow(*_: object, **__: object) -> int:
    # Behaves like Podman.run() for "podman logs -f": runs until cancelled, then exits
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        return 130
    return 0


@unittest.skipIf(sys.platform == "win32", "SIGINT handler is not used on Windows")
class TestComposeLogs(unittest.TestCase):
    def test_ctrl_c_stops_follow_without_error(self) -> None:
        compose = mock.Mock()
        compose.assert_services = mock.Mock()
        compose.containers = [
            {"_service": "web", "log_prefix": "web"},
            {"_service": "db", "log_prefix": "db"},
        ]
        compose.container_names_by_service = {"web": ["proj_web_1"], "db": ["proj_db_1"]}
        compose.console_colors = ["\x1b[1;32m"]
        compose.podman.run = mock.AsyncMock(side_effect=podman_logs_follow)
        args = Namespace(
            services=["web", "db"],
            latest=False,
            follow=True,
            names=False,
            no_color=False,
            no_log_prefix=False,
            since=None,
            tail="all",
            timestamps=False,
            until=None,
        )

        async def logs_then_ctrl_c() -> None:
            asyncio.get_running_loop().call_later(0.1, signal.raise_signal, signal.SIGINT)
            return await compose_logs(compose, args)

        try:
            result = asyncio.run(logs_then_ctrl_c())
        except (KeyboardInterrupt, asyncio.CancelledError) as e:
            self.fail(f"Ctrl+C on 'logs -f' raised {type(e).__name__}")

        self.assertIsNone(result)
        self.assertEqual(compose.podman.run.call_count, 2)
