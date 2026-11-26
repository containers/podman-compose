# SPDX-License-Identifier: GPL-2.0
# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
import os
import tempfile
import unittest

import yaml

from podman_compose import PodmanCompose
from podman_compose import parse_short_mount


class ParseShortMountTests(unittest.TestCase):
    def test_multi_propagation(self) -> None:
        self.assertEqual(
            parse_short_mount("/foo/bar:/baz:U,Z", "/"),
            {
                "type": "bind",
                "source": "/foo/bar",
                "target": "/baz",
                "bind": {
                    "propagation": "U,Z",
                },
            },
        )


class ParseComposeFileVolumeTests(unittest.TestCase):
    def test_long_syntax_volume_without_source(self) -> None:
        compose = {
            "services": {
                "app": {
                    "image": "alpine:3.20",
                    "volumes": [
                        {"type": "volume", "target": "/tmp", "volume": {"labels": {"a": "b"}}}
                    ],
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            compose_file = os.path.join(tmp_dir, "compose.yaml")
            with open(compose_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(compose, f)

            podman_compose = PodmanCompose()
            podman_compose.global_args.file = [compose_file]
            podman_compose.global_args.project_name = "test_project"
            podman_compose.global_args.env_file = None
            podman_compose.global_args.profile = []
            podman_compose.global_args.in_pod = "false"

            podman_compose._parse_compose_file()

        self.assertEqual(len(podman_compose.containers), 1)
