# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import os
import tempfile
import unittest

import yaml

from podman_compose import PodmanCompose
from podman_compose import normalize_service


class TestAnonymousVolumeLongSyntax(unittest.TestCase):
    def test_parse_compose_file_accepts_volume_without_source(self) -> None:
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

    def test_normalize_service_keeps_volume_without_source(self) -> None:
        service = {"volumes": [{"type": "volume", "target": "/tmp"}]}

        normalized = normalize_service(service, sub_dir="sub")

        self.assertEqual(normalized["volumes"], [{"type": "volume", "target": "/tmp"}])
