# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanCompose(unittest.TestCase, RunSubprocessMixin):
    up_cmd = [
        "coverage",
        "run",
        podman_compose_path(),
        "-f",
        os.path.join(test_path(), "up_down", "docker-compose.yml"),
        "up",
        "-d",
        "--force-recreate",
    ]

    def setUp(self) -> None:
        """
        Retag the debian image before each test to not mess with the other integration tests when
        testing the `--rmi` argument
        """
        tag_cmd = [
            "podman",
            "tag",
            "docker.io/library/debian:bookworm-slim",
            "docker.io/library/debian:up-down-test",
        ]
        self.run_subprocess_assert_returncode(tag_cmd)

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Ensures that the images that were created for this tests will be removed
        """
        rmi_cmd = [
            "podman",
            "rmi",
            "--force",
            "--ignore",
            "podman-compose-up-down-test",
            "docker.io/library/debian:up-down-test",
        ]
        cls().run_subprocess_assert_returncode(rmi_cmd)

    def test_down(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose.yml"),
            "down",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"])
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"])
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "podman-compose-up-down-test",
        ])
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "docker.io/library/debian:up-down-test",
        ])

    def test_down_with_volumes(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose.yml"),
            "down",
            "--volumes",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"], 1)
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"], 1)
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "podman-compose-up-down-test",
        ])
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "docker.io/library/debian:up-down-test",
        ])

    def test_down_without_orphans(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose-orphans.yml"),
            "down",
            "--volumes",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "container", "exists", "up_down_web2_1"])
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"], 1)
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"])
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "podman-compose-up-down-test",
        ])
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "docker.io/library/debian:up-down-test",
        ])

        # Cleanup orphaned container
        down_all_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose.yml"),
            "down",
            "--volumes",
            "--timeout",
            "0",
        ]
        self.run_subprocess_assert_returncode(down_all_cmd)
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"], 1)

    def test_down_with_orphans(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose-orphans.yml"),
            "down",
            "--volumes",
            "--remove-orphans",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"], 1)
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"], 1)
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "podman-compose-up-down-test",
        ])
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "docker.io/library/debian:up-down-test",
        ])

    def test_down_with_images_default(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose.yml"),
            "down",
            "--rmi",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"])
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"])
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", "podman-compose-up-down-test"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", "docker.io/library/debian:up-down-test"], 1
        )

    def test_down_with_images_all(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose.yml"),
            "down",
            "--rmi",
            "all",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"])
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"])
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", "podman-compose-up-down-test"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", "docker.io/library/debian:up-down-test"], 1
        )

    def test_down_with_images_all_and_orphans(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose-orphans.yml"),
            "down",
            "--volumes",
            "--remove-orphans",
            "--rmi",
            "all",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"], 1)
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"], 1)
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", "podman-compose-up-down-test"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", "docker.io/library/debian:up-down-test"], 1
        )

    def test_down_with_images_local(self) -> None:
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "up_down", "docker-compose.yml"),
            "down",
            "--rmi",
            "local",
            "--timeout",
            "0",
        ]

        try:
            self.run_subprocess_assert_returncode(self.up_cmd)
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web1_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "container",
                "exists",
                "up_down_web2_1",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web1_vol",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "volume",
                "exists",
                "up_down_web2_vol",
            ])
        finally:
            self.run_subprocess_assert_returncode(down_cmd)

        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web1_1"], 1
        )
        self.run_subprocess_assert_returncode(
            ["podman", "container", "exists", "up_down_web2_1"], 1
        )
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web1_vol"])
        self.run_subprocess_assert_returncode(["podman", "volume", "exists", "up_down_web2_vol"])
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", "podman-compose-up-down-test"], 1
        )
        self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "exists",
            "docker.io/library/debian:up-down-test",
        ])
