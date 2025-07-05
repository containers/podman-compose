# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(version: str = '1') -> str:
    return os.path.join(os.path.join(test_path(), "no_recreate"), f"compose{version}.yaml")


class TestComposeNoRecreate(unittest.TestCase, RunSubprocessMixin):
    def test_no_recreate(self) -> None:
        def up(args: list[str] = [], version: str = '1') -> None:
            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(version),
                    "up",
                    "-t",
                    "0",
                    "-d",
                    *args,
                ],
            )

        def get_container_id() -> bytes:
            return self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
                "--format",
                '{{.ID}}',
            ])[0]

        try:
            up()

            container_id = get_container_id()

            self.assertGreater(len(container_id), 0)

            # Default behavior - up with same compose file should not recreate the container
            up()
            self.assertEqual(get_container_id(), container_id)

            # Default behavior - up with modified compose file should recreate the container
            up(version='2')
            self.assertNotEqual(get_container_id(), container_id)

            container_id = get_container_id()

            # Using --no-recreate should not recreate the container
            # even if the compose file is modified
            up(["--no-recreate"], version='1')
            self.assertEqual(get_container_id(), container_id)

            # Using --force-recreate should recreate the container
            # even if the compose file is not modified
            up(["--force-recreate"], version='1')
            self.assertNotEqual(get_container_id(), container_id)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
