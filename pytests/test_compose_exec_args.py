# SPDX-License-Identifier: GPL-2.0

import argparse
import unittest

from podman_compose import compose_exec_args


class TestComposeExecArgs(unittest.TestCase):
    def test_minimal(self):
        cnt = get_minimal_container()
        args = get_minimal_args()

        result = compose_exec_args(cnt, "container_name", args)
        expected = ["--interactive", "--tty", "container_name"]
        self.assertEqual(result, expected)

    def test_additional_env_value_equals(self):
        cnt = get_minimal_container()
        args = get_minimal_args()
        args.env = ["key=valuepart1=valuepart2"]

        result = compose_exec_args(cnt, "container_name", args)
        expected = [
            "--interactive",
            "--tty",
            "--env",
            "key=valuepart1=valuepart2",
            "container_name",
        ]
        self.assertEqual(result, expected)


def get_minimal_container():
    return {}


def get_minimal_args():
    return argparse.Namespace(
        T=None,
        cnt_command=None,
        env=None,
        privileged=None,
        user=None,
        workdir=None,
    )
