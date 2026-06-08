# SPDX-License-Identifier: GPL-2.0

import argparse
import unittest

from podman_compose import compose_cp_args


class TestComposeCpArgs(unittest.TestCase):
    def test_cp_host_to_container(self) -> None:
        args = get_minimal_args()
        args.src = "host_file.txt"
        args.dst = "my-service:/tmp/copied_from_host.txt"

        self.assertEqual(
            compose_cp_args("container_name", args),
            ['--archive', 'host_file.txt', 'container_name:/tmp/copied_from_host.txt'],
        )

    def test_cp_container_to_host(self) -> None:
        args = get_minimal_args()
        args.src = "container_name:host_file.txt"
        args.dst = "/tmp/container_file.txt"

        self.assertEqual(
            compose_cp_args("container_name", args),
            ['--archive', 'container_name:host_file.txt', '/tmp/container_file.txt'],
        )

    def test_archive_and_overwrite_non_default(self) -> None:
        args = get_minimal_args()
        args.archive = False
        args.overwrite = True
        args.src = "container_name:host_file.txt"
        args.dst = "/tmp/container_file.txt"

        self.assertEqual(
            compose_cp_args("container_name", args),
            ['--overwrite', 'container_name:host_file.txt', '/tmp/container_file.txt'],
        )


def get_minimal_args() -> argparse.Namespace:
    return argparse.Namespace(archive=True, overwrite=None)
