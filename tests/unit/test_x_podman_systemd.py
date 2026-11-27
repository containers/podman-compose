# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any

import yaml

from podman_compose import PodmanCompose
from podman_compose import PodmanComposeError


class TestParseComposeFileXPodmanSystemd(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.podman_compose = PodmanCompose()
        self.podman_compose.global_args.file = [self.path("docker-compose.yml")]
        self.podman_compose.global_args.project_name = "test_project"
        self.podman_compose.global_args.env_file = None
        self.podman_compose.global_args.profile = []
        self.podman_compose.global_args.in_pod = "false"

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def path(self, name: str) -> str:
        return os.path.join(self.tmp_dir.name, name)

    def write_yaml(self, name: str, content: dict[str, Any]) -> None:
        with open(self.path(name), "w", encoding="utf-8") as f:
            yaml.safe_dump(content, f)

    def test_invalid_value_from_extends_file_raises(self) -> None:
        self.write_yaml(
            "base.yml",
            {"services": {"base": {"image": "busybox", "x-podman.systemd": "bogus"}}},
        )
        self.write_yaml(
            "docker-compose.yml",
            {"services": {"b": {"extends": {"file": "base.yml", "service": "base"}}}},
        )

        with self.assertRaises(PodmanComposeError) as context:
            self.podman_compose._parse_compose_file()
        self.assertEqual(
            "services.b.x-podman.systemd must be true, false or always, got 'bogus'",
            str(context.exception),
        )

    def test_valid_value_from_extends_file_passes(self) -> None:
        self.write_yaml(
            "base.yml",
            {"services": {"base": {"image": "busybox", "x-podman.systemd": "always"}}},
        )
        self.write_yaml(
            "docker-compose.yml",
            {"services": {"b": {"extends": {"file": "base.yml", "service": "base"}}}},
        )

        self.podman_compose._parse_compose_file()

        self.assertEqual(self.podman_compose.services["b"]["x-podman.systemd"], "always")
