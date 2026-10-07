# SPDX-License-Identifier: GPL-2.0

import json
import os
import textwrap
import unittest
from io import BytesIO

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "extends_w_file_nested"), "docker-compose.yml")


class TestComposeExtendsWithFileNested(unittest.TestCase, RunSubprocessMixin):
    """
    ``important_web`` extends ``child`` from an external file, and ``child``
    itself extends ``base`` from that same file.  The whole ``extends`` chain
    must be resolved, so ``important_web`` inherits the base image and mounts.
    """

    def test_extends_w_file_nested(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "-d",
            ])

            web = self._inspect("extends_w_file_nested_web_1")
            self.assertEqual(web["ImageName"], "localhost/nopush/podman-compose-test:latest")
            self.assertEqual(self._mount_destinations(web), {"/data"})

            important_web = self._inspect("extends_w_file_nested_important_web_1")
            self.assertEqual(
                important_web["ImageName"], "localhost/nopush/podman-compose-test:latest"
            )
            self.assertEqual(self._mount_destinations(important_web), {"/data", "/logs"})
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_config_shows_resolved_extends(self) -> None:
        out, _ = self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_yaml_path(),
            "config",
        ])
        expected = textwrap.dedent("""\
            services:
              important_web:
                command:
                - /bin/sh
                image: nopush/podman-compose-test
                volumes:
                - /data
                - /logs
              web:
                command:
                - /bin/sh
                image: nopush/podman-compose-test
                volumes:
                - /data

            """)
        self.assertEqual(out.decode("utf-8"), expected)

    def _inspect(self, container_name: str) -> dict:
        output, _ = self.run_subprocess_assert_returncode([
            "podman",
            "inspect",
            container_name,
        ])
        inspect = json.load(BytesIO(output))
        self.assertEqual(len(inspect), 1)
        return inspect[0]

    @staticmethod
    def _mount_destinations(container: dict) -> set[str]:
        return {mount["Destination"] for mount in container.get("Mounts", [])}
