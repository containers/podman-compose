# SPDX-License-Identifier: GPL-2.0

import unittest

from parameterized import parameterized

from podman_compose import PodmanCompose
from podman_compose import default_network_name_for_project


def create_compose(project_name: str, x_podman: dict) -> PodmanCompose:
    compose = PodmanCompose()
    compose.project_name = project_name
    compose.x_podman = x_podman
    return compose


class TestDefaultNetworkName(unittest.TestCase):
    @parameterized.expand([
        ("default", "my-project", {}, "my-project_default"),
        (
            "name_separator_compat",
            "my-project",
            {PodmanCompose.XPodmanSettingKey.NAME_SEPARATOR_COMPAT: True},
            "my-project_default",
        ),
        (
            "default_net_name_compat",
            "my-project",
            {PodmanCompose.XPodmanSettingKey.DEFAULT_NET_NAME_COMPAT: True},
            "myproject_default",
        ),
        (
            "both_compat",
            "my-project",
            {
                PodmanCompose.XPodmanSettingKey.NAME_SEPARATOR_COMPAT: True,
                PodmanCompose.XPodmanSettingKey.DEFAULT_NET_NAME_COMPAT: True,
            },
            "myproject_default",
        ),
    ])
    def test_default_network_name(
        self, _: str, project_name: str, x_podman: dict, expected: str
    ) -> None:
        compose = create_compose(project_name, x_podman)
        self.assertEqual(default_network_name_for_project(compose, "default", False), expected)

    def test_external_network_keeps_its_name(self) -> None:
        compose = create_compose(
            "my-project", {PodmanCompose.XPodmanSettingKey.NAME_SEPARATOR_COMPAT: True}
        )
        self.assertEqual(
            default_network_name_for_project(compose, "shared-net", True), "shared-net"
        )
