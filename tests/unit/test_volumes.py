# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access,redefined-outer-name
import argparse
import hashlib
import os
import tempfile
import unittest

import yaml

from podman_compose import PodmanCompose
from podman_compose import normalize_service
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


class AnonymousVolumeTests(unittest.TestCase):
    """An anonymous volume in long syntax omits `source`, which is not an error."""

    def _parse(self, service: dict) -> PodmanCompose:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "docker-compose.yaml")
            with open(path, "w", encoding="utf-8") as stream:
                yaml.safe_dump({"services": {"test-service": service}}, stream)

            compose = PodmanCompose()
            compose.global_args = argparse.Namespace(
                file=[path],
                project_name=None,
                env_file=None,
                profile=[],
                in_pod="1",
                pod_args=None,
                no_normalize=None,
            )
            compose._parse_compose_file()
            return compose

    def test_long_syntax_without_source_is_parsed(self) -> None:
        compose = self._parse({
            "image": "test-image",
            "volumes": [{"type": "volume", "target": "/data"}],
        })

        (volume,) = compose.services["test-service"]["volumes"]
        self.assertNotIn("source", volume)
        # No source to name it after, so the volume is named for the service and target.
        self.assertTrue(
            volume["_vol"]["name"].endswith(
                hashlib.sha256(b"/data").hexdigest(),
            )
        )

    def test_named_volume_missing_from_top_level_is_still_refused(self) -> None:
        with self.assertRaises(RuntimeError):
            self._parse({
                "image": "test-image",
                "volumes": [{"type": "volume", "source": "undeclared", "target": "/data"}],
            })

    def test_normalize_service_leaves_a_missing_source_alone(self) -> None:
        service = {
            "image": "test-image",
            "volumes": [{"type": "volume", "target": "/data"}],
        }

        self.assertEqual(
            normalize_service(service, sub_dir="./sub")["volumes"],
            [{"type": "volume", "target": "/data"}],
        )

    def test_normalize_service_still_rewrites_a_relative_source(self) -> None:
        service = {
            "image": "test-image",
            "volumes": [{"type": "bind", "source": "./data", "target": "/data"}],
        }

        self.assertEqual(
            normalize_service(service, sub_dir="./sub")["volumes"],
            [{"type": "bind", "source": "./sub/./data", "target": "/data"}],
        )
