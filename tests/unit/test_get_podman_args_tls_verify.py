# SPDX-License-Identifier: GPL-2.0

import argparse
import unittest

from parameterized import parameterized

from podman_compose import PodmanCompose


def compose_with_tls_verify(tls_verify: str) -> PodmanCompose:
    compose = PodmanCompose()
    compose.global_args = argparse.Namespace(
        podman_args=[],
        tls_verify=tls_verify,
        podman_pull_args=[],
        podman_push_args=[],
        podman_build_args=[],
        podman_run_args=[],
        podman_inspect_args=[],
        podman_start_args=[],
        podman_stop_args=[],
        podman_rm_args=[],
        podman_volume_args=[],
    )
    return compose


class TestGetPodmanArgsTlsVerify(unittest.TestCase):
    @parameterized.expand([
        ("pull",),
        ("push",),
        ("build",),
    ])
    def test_tls_verify_true_registry_commands_no_tls_flag(self, cmd: str) -> None:
        compose = compose_with_tls_verify("true")
        xargs = compose.get_podman_args(cmd)
        self.assertNotIn("--tls-verify=false", xargs)

    @parameterized.expand([
        ("pull",),
        ("push",),
        ("build",),
    ])
    def test_tls_verify_false_registry_commands_injects_flag(self, cmd: str) -> None:
        compose = compose_with_tls_verify("false")
        xargs = compose.get_podman_args(cmd)
        self.assertIn("--tls-verify=false", xargs)
        self.assertEqual(len([a for a in xargs if a.startswith("--tls-verify")]), 1)

    @parameterized.expand([
        ("run",),
        ("start",),
        ("stop",),
        ("rm",),
        ("inspect",),
        ("volume",),
    ])
    def test_tls_verify_false_non_registry_commands_no_tls_flag(self, cmd: str) -> None:
        compose = compose_with_tls_verify("false")
        xargs = compose.get_podman_args(cmd)
        self.assertNotIn("--tls-verify=false", xargs)

    def test_tls_verify_false_with_podman_pull_args(self) -> None:
        compose = compose_with_tls_verify("false")
        compose.global_args.podman_pull_args = ["--quiet"]
        xargs = compose.get_podman_args("pull")
        self.assertIn("--tls-verify=false", xargs)
        self.assertIn("--quiet", xargs)
