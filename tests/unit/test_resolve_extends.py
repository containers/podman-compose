# SPDX-License-Identifier: GPL-2.0
from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any

from podman_compose import PodmanComposeError
from podman_compose import flat_deps
from podman_compose import normalize
from podman_compose import resolve_extends


def _resolve(services: dict[str, Any]) -> dict[str, Any]:
    """Run the same normalize/flat_deps/resolve_extends sequence as parsing."""
    normalize({"services": services})
    flat_deps(services, with_extends=True)
    service_names = sorted((len(srv["_deps"]), name) for name, srv in services.items())
    resolve_extends(services, [name for _, name in service_names], {})
    return services


class TestResolveExtends(unittest.TestCase):
    def test_nested_extends_same_file(self) -> None:
        services: dict[str, Any] = {
            "base": {
                "image": "nopush/podman-compose-test",
                "volumes": ["/tmp/base:/tmp/base:rw"],
            },
            "mid": {
                "extends": {"service": "base"},
                "volumes": ["/tmp/mid:/tmp/mid:rw"],
            },
            "top": {
                "extends": {"service": "mid"},
                "volumes": ["/tmp/top:/tmp/top:rw"],
            },
        }

        _resolve(services)

        self.assertEqual(services["top"]["image"], "nopush/podman-compose-test")
        self.assertEqual(
            services["top"]["volumes"],
            ["/tmp/base:/tmp/base:rw", "/tmp/mid:/tmp/mid:rw", "/tmp/top:/tmp/top:rw"],
        )
        self.assertNotIn("extends", services["top"])

    def test_nested_extends_across_file(self) -> None:
        general = """
services:
  base:
    command: [/bin/sh]
    image: nopush/podman-compose-test
    volumes:
      - /data

  child:
    extends:
      service: base
    volumes:
      - /logs
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            general_path = os.path.join(tmp_dir, "docker-compose-general.yml")
            with open(general_path, "w", encoding="utf-8") as f:
                f.write(general)

            services: dict[str, Any] = {
                "web": {"extends": {"file": general_path, "service": "base"}},
                "important_web": {"extends": {"file": general_path, "service": "child"}},
            }

            _resolve(services)

            self.assertEqual(services["web"]["image"], "nopush/podman-compose-test")
            self.assertEqual(services["web"]["volumes"], ["/data"])
            self.assertEqual(services["important_web"]["image"], "nopush/podman-compose-test")
            self.assertEqual(services["important_web"]["volumes"], ["/data", "/logs"])

    def test_nested_extends_across_file_normalizes_paths(self) -> None:
        """Relative paths of a same-file base inside an external file are kept."""
        general = """
services:
  base:
    image: nopush/podman-compose-test
    volumes:
      - ./data:/data:rw

  mid:
    extends:
      service: base
    volumes:
      - ./mid:/mid:rw
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            general_path = os.path.join(tmp_dir, "docker-compose-general.yml")
            with open(general_path, "w", encoding="utf-8") as f:
                f.write(general)

            services: dict[str, Any] = {
                "top": {"extends": {"file": general_path, "service": "mid"}}
            }

            _resolve(services)

            self.assertEqual(services["top"]["image"], "nopush/podman-compose-test")
            self.assertEqual(
                services["top"]["volumes"],
                [f"{tmp_dir}/./data:/data:rw", f"{tmp_dir}/./mid:/mid:rw"],
            )

    def test_circular_extends_raises(self) -> None:
        services: dict[str, Any] = {
            "a": {"extends": {"service": "b"}},
            "b": {"extends": {"service": "a"}},
        }

        with self.assertRaises(PodmanComposeError):
            _resolve(services)

    def test_missing_service_same_file_raises(self) -> None:
        services: dict[str, Any] = {"web": {"extends": {"service": "does_not_exist"}}}

        with self.assertRaises(PodmanComposeError):
            _resolve(services)

    def test_missing_service_in_external_file_raises(self) -> None:
        general = """
services:
  base:
    image: nopush/podman-compose-test
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            general_path = os.path.join(tmp_dir, "docker-compose-general.yml")
            with open(general_path, "w", encoding="utf-8") as f:
                f.write(general)

            services: dict[str, Any] = {
                "web": {"extends": {"file": general_path, "service": "missing"}}
            }

            with self.assertRaises(PodmanComposeError):
                _resolve(services)

    def test_empty_service_in_main_file_raises(self) -> None:
        """An empty service in the main file is rejected, like docker-compose."""
        services: dict[str, Any] = {"webapp_default": None}

        with self.assertRaises(PodmanComposeError) as ctx:
            _resolve(services)

        self.assertIn("must be a mapping", str(ctx.exception))

    def test_extends_empty_service_in_external_file(self) -> None:
        general = """
services:
  webapp_default:

  webapp_special:
    image: nopush/podman-compose-test
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            general_path = os.path.join(tmp_dir, "common-services.yml")
            with open(general_path, "w", encoding="utf-8") as f:
                f.write(general)

            services: dict[str, Any] = {
                "web": {
                    "extends": {"file": general_path, "service": "webapp_default"},
                    "image": "nopush/podman-compose-test",
                }
            }

            _resolve(services)

            self.assertEqual(services["web"]["image"], "nopush/podman-compose-test")
            self.assertNotIn("extends", services["web"])

    def test_nested_relative_file_resolved_against_declaring_file(self) -> None:
        """A nested ``extends.file`` is relative to the file that declares it."""
        a_yml = """
services:
  mid:
    extends:
      file: b.yml
      service: base
    volumes:
      - /mid
"""
        b_yml = """
services:
  base:
    image: nopush/podman-compose-test
    volumes:
      - /base
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            sub_dir = os.path.join(tmp_dir, "sub")
            os.makedirs(sub_dir)
            with open(os.path.join(sub_dir, "a.yml"), "w", encoding="utf-8") as f:
                f.write(a_yml)
            with open(os.path.join(sub_dir, "b.yml"), "w", encoding="utf-8") as f:
                f.write(b_yml)

            services: dict[str, Any] = {
                "top": {"extends": {"file": os.path.join(sub_dir, "a.yml"), "service": "mid"}}
            }

            _resolve(services)

            self.assertEqual(services["top"]["image"], "nopush/podman-compose-test")
            self.assertEqual(services["top"]["volumes"], ["/base", "/mid"])

    def test_no_false_positive_cycle_across_files(self) -> None:
        a_yml = """
services:
  x:
    extends:
      service: z
  z:
    extends:
      file: b.yml
      service: y
    volumes:
      - /a_z
"""
        b_yml = """
services:
  y:
    extends:
      service: z
  z:
    image: nopush/podman-compose-test
    volumes:
      - /b_z
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            a_path = os.path.join(tmp_dir, "a.yml")
            b_path = os.path.join(tmp_dir, "b.yml")
            with open(a_path, "w", encoding="utf-8") as f:
                f.write(a_yml)
            with open(b_path, "w", encoding="utf-8") as f:
                f.write(b_yml)

            services: dict[str, Any] = {"top": {"extends": {"file": a_path, "service": "x"}}}

            _resolve(services)

            self.assertEqual(services["top"]["image"], "nopush/podman-compose-test")
            self.assertEqual(services["top"]["volumes"], ["/b_z", "/a_z"])

    def test_external_build_string_is_normalized(self) -> None:
        general = """
services:
  base:
    build: .
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            general_path = os.path.join(tmp_dir, "docker-compose-general.yml")
            with open(general_path, "w", encoding="utf-8") as f:
                f.write(general)

            services: dict[str, Any] = {
                "web": {"extends": {"file": general_path, "service": "base"}}
            }

            _resolve(services)

            self.assertIsInstance(services["web"]["build"], dict)
            self.assertIn("context", services["web"]["build"])


if __name__ == "__main__":
    unittest.main()
