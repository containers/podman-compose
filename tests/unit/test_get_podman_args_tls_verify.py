# SPDX-License-Identifier: GPL-2.0

import argparse
import unittest

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
    def test_tls_verify_true_pull_push_build_no_flag(self) -> None:
        compose = compose_with_tls_verify("true")
        for cmd in ("pull", "push", "build"):
            xargs = compose.get_podman_args(cmd)
            self.assertNotIn("--tls-verify=false", xargs, f"cmd={cmd} should not get --tls-verify=false when tls_verify=true")

    def test_tls_verify_false_pull_injects_flag(self) -> None:
        compose = compose_with_tls_verify("false")
        xargs = compose.get_podman_args("pull")
        self.assertIn("--tls-verify=false", xargs)
        self.assertEqual(xargs[0], "--tls-verify=false")

    def test_tls_verify_false_push_injects_flag(self) -> None:
        compose = compose_with_tls_verify("false")
        xargs = compose.get_podman_args("push")
        self.assertIn("--tls-verify=false", xargs)
        self.assertEqual(xargs[0], "--tls-verify=false")

    def test_tls_verify_false_build_injects_flag(self) -> None:
        compose = compose_with_tls_verify("false")
        xargs = compose.get_podman_args("build")
        self.assertIn("--tls-verify=false", xargs)
        self.assertEqual(xargs[0], "--tls-verify=false")

    def test_tls_verify_false_non_registry_commands_no_flag(self) -> None:
        compose = compose_with_tls_verify("false")
        for cmd in ("run", "start", "stop", "rm", "inspect", "volume"):
            xargs = compose.get_podman_args(cmd)
            self.assertNotIn("--tls-verify=false", xargs, f"cmd={cmd} must not get --tls-verify=false")

    def test_tls_verify_false_with_podman_pull_args(self) -> None:
        compose = compose_with_tls_verify("false")
        compose.global_args.podman_pull_args = ["--quiet"]
        xargs = compose.get_podman_args("pull")
        self.assertEqual(xargs[0], "--tls-verify=false")
        self.assertIn("--quiet", xargs)
