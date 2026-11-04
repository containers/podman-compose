# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import argparse
import os
import tempfile
import unittest

from podman_compose import PodmanCompose
from podman_compose import compose_up_parse

COMPOSE_YAML = """
services:
    client:
        image: busybox
    bootstrap:
        image: busybox
        deploy:
            mode: replicated
            replicas: 2
    worker:
        image: busybox
        scale: 3
"""


def container_counts(scale: list[str] | None) -> dict[str, int]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        compose_file = os.path.join(tmp_dir, "docker-compose.yaml")
        with open(compose_file, "w", encoding="utf-8") as f:
            f.write(COMPOSE_YAML)

        podman_compose = PodmanCompose()
        podman_compose.global_args = argparse.Namespace(
            file=[compose_file],
            project_name="test_proj",
            env_file=None,
            profile=[],
            in_pod="false",
            pod_args=None,
            no_normalize=False,
            scale=scale,
        )
        podman_compose._parse_compose_file()

    counts: dict[str, int] = {}
    for cnt in podman_compose.containers:
        counts[cnt["_service"]] = counts.get(cnt["_service"], 0) + 1
    return counts


class TestScale(unittest.TestCase):
    def test_no_scale_arg(self) -> None:
        self.assertEqual(container_counts(None), {"client": 1, "bootstrap": 2, "worker": 3})

    def test_single_scale_arg(self) -> None:
        self.assertEqual(container_counts(["client=3"]), {"client": 3, "bootstrap": 2, "worker": 3})

    def test_multiple_scale_args(self) -> None:
        self.assertEqual(
            container_counts(["client=3", "bootstrap=4"]),
            {"client": 3, "bootstrap": 4, "worker": 3},
        )

    def test_scale_arg_repeated_for_same_service(self) -> None:
        self.assertEqual(
            container_counts(["worker=5", "worker=2"]),
            {"client": 1, "bootstrap": 2, "worker": 2},
        )

    def test_up_parser_collects_scale_args(self) -> None:
        parser = argparse.ArgumentParser()
        compose_up_parse(parser)

        args = parser.parse_args(["--scale", "client=3", "--scale", "bootstrap=4"])
        self.assertEqual(args.scale, ["client=3", "bootstrap=4"])

        args = parser.parse_args([])
        self.assertIsNone(args.scale)
