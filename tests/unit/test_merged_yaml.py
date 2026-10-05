# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access
from __future__ import annotations

import os
import tempfile
import unittest

from podman_compose import PodmanCompose


class TestMergedYaml(unittest.TestCase):
    def test_merged_yaml_keeps_non_ascii_characters(self) -> None:
        content = """\
services:
  sample:
    image: nopush/podman-compose-test
    volumes:
    - /home/développement:/home/dev
"""

        with tempfile.TemporaryDirectory() as tmp_dir:
            compose_file = os.path.join(tmp_dir, "docker-compose.yaml")
            with open(compose_file, "w", encoding="utf-8") as f:
                f.write(content)

            podman_compose = PodmanCompose()
            podman_compose.global_args.file = [compose_file]
            podman_compose.global_args.project_name = "test_project"
            podman_compose.global_args.env_file = None
            podman_compose.global_args.profile = []
            podman_compose.global_args.in_pod = "false"
            podman_compose._parse_compose_file()

        self.assertIn("/home/développement", podman_compose.merged_yaml)
