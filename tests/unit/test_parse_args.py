# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from unittest import mock

from podman_compose import PodmanCompose


class TestParseArgs(unittest.TestCase):
    def test_compose_env_files(self) -> None:
        compose = PodmanCompose()

        with mock.patch.dict(
            os.environ,
            {"COMPOSE_ENV_FILES": ".env.default,.env.override"},
        ):
            args = compose._parse_args(["--version"])  # pylint: disable=protected-access

        self.assertEqual(args.env_file, [".env.default", ".env.override"])

    def test_env_file_flag_overrides_compose_env_files(self) -> None:
        compose = PodmanCompose()

        with mock.patch.dict(
            os.environ,
            {"COMPOSE_ENV_FILES": ".env.default,.env.override"},
        ):
            args = compose._parse_args(  # pylint: disable=protected-access
                ["--env-file", ".env.cli", "--version"]
            )

        self.assertEqual(args.env_file, [".env.cli"])
