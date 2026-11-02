# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from unittest import mock

from podman_compose import PodmanCompose


class TestEnvFileInterpolation(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.compose_file = os.path.join(self._tmp.name, "docker-compose.yaml")
        with open(self.compose_file, "w", encoding="utf-8") as fh:
            fh.write("services:\n  app:\n    image: busybox\n")

    def write_env(self, name: str, content: str) -> str:
        path = os.path.join(self._tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def parse(self, env_files: list[str]) -> PodmanCompose:
        podman_compose = PodmanCompose()
        podman_compose.global_args = argparse.Namespace(
            file=[self.compose_file],
            project_name="test_proj",
            env_file=env_files,
            profile=[],
            in_pod="false",
            pod_args=None,
            no_normalize=False,
        )
        podman_compose._parse_compose_file()
        return podman_compose

    def test_env_file_interpolates_from_earlier_env_file(self) -> None:
        first = self.write_env("a.env", "CROSS_FILE_BAR=bar\n")
        second = self.write_env("b.env", "CROSS_FILE_FOO=${CROSS_FILE_BAR}\n")

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CROSS_FILE_BAR", None)
            podman_compose = self.parse([first, second])

        self.assertEqual(podman_compose.environ["CROSS_FILE_FOO"], "bar")

    def test_process_environment_wins_over_env_file_for_interpolation(self) -> None:
        first = self.write_env("a.env", "CROSS_FILE_BAR=from-file\n")
        second = self.write_env("b.env", "CROSS_FILE_FOO=${CROSS_FILE_BAR}\n")

        with mock.patch.dict(os.environ, {"CROSS_FILE_BAR": "from-environ"}):
            podman_compose = self.parse([first, second])

        self.assertEqual(podman_compose.environ["CROSS_FILE_FOO"], "from-environ")
