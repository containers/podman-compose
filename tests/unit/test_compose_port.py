# SPDX-License-Identifier: GPL-2.0

import argparse
import io
import json
import unittest
from contextlib import redirect_stdout
from typing import Any
from unittest import mock

from parameterized import parameterized

from podman_compose import compose_port


def create_compose_mock(host_ip: str) -> mock.Mock:
    compose = mock.Mock()
    compose.assert_services = mock.Mock()
    compose.container_names_by_service = {"web": ["project_web_1"]}
    inspect = [
        {"NetworkSettings": {"Ports": {"8080/tcp": [{"HostIp": host_ip, "HostPort": "49153"}]}}}
    ]

    async def podman_output(*args: Any, **kwargs: Any) -> bytes:
        return json.dumps(inspect).encode("utf-8")

    compose.podman.output = mock.Mock(side_effect=podman_output)
    return compose


class TestComposePort(unittest.IsolatedAsyncioTestCase):
    @parameterized.expand([
        ("all_interfaces", "", "0.0.0.0:49153"),
        ("ipv4", "127.0.0.1", "127.0.0.1:49153"),
        ("ipv6", "::1", "[::1]:49153"),
    ])
    async def test_prints_host_ip_and_port(self, _: str, host_ip: str, output: str) -> None:
        compose = create_compose_mock(host_ip)
        args = argparse.Namespace(service="web", index=1, private_port=8080, protocol="tcp")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            await compose_port(compose, args)

        self.assertEqual(stdout.getvalue(), output + "\n")
