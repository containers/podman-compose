# SPDX-License-Identifier: GPL-2.0
import os
import unittest

from packaging import version

from tests.integration.test_utils import PodmanAwareRunSubprocessMixin
from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import is_systemd_available
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(suffix: str = "") -> str:
    return os.path.join(os.path.join(test_path(), "deps"), f"docker-compose{suffix}.yaml")


class TestComposeBaseDeps(unittest.TestCase, RunSubprocessMixin):
    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_deps(self) -> None:
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "--rm",
                "sleep",
                "/bin/sh",
                "-c",
                "wget -O - http://web:8000/hosts",
            ])
            self.assertIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertIn(b"deps_web_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_run_nodeps(self) -> None:
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "run",
                "--rm",
                "--no-deps",
                "sleep",
                "/bin/sh",
                "-c",
                "wget -O - http://web:8000/hosts || echo Failed to connect",
            ])
            self.assertNotIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertNotIn(b"deps_web_1", output)
            self.assertIn(b"Failed to connect", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    def test_up_nodeps(self) -> None:
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "up",
                "--no-deps",
                "--detach",
                "sleep",
            ])
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
            ])
            self.assertNotIn(b"deps_web_1", output)
            self.assertIn(b"deps_sleep_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])

    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_podman_compose_run(self) -> None:
        """
        This will test depends_on as well
        """
        run_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "deps", "docker-compose.yaml"),
            "run",
            "--rm",
            "sleep",
            "/bin/sh",
            "-c",
            "wget -q -O - http://web:8000/hosts",
        ]

        out, _ = self.run_subprocess_assert_returncode(run_cmd)
        self.assertIn(b"127.0.0.1\tlocalhost", out)

        # Run it again to make sure we can run it twice. I saw an issue where a second run, with
        # the container left up, would fail
        run_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "deps", "docker-compose.yaml"),
            "run",
            "--rm",
            "sleep",
            "/bin/sh",
            "-c",
            "wget -q -O - http://web:8000/hosts",
        ]

        out, _ = self.run_subprocess_assert_returncode(run_cmd)
        self.assertIn(b"127.0.0.1\tlocalhost", out)

        # This leaves a container running. Not sure it's intended, but it matches docker-compose
        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "deps", "docker-compose.yaml"),
            "down",
        ]

        self.run_subprocess_assert_returncode(down_cmd)


class TestComposeConditionalDeps(unittest.TestCase, RunSubprocessMixin):
    @unittest.skipIf(get_podman_version() >= version.parse("5.0.0"), "Breaks as of podman-5.4.2.")
    def test_deps_succeeds(self) -> None:
        suffix = "-conditional-succeeds"
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "run",
                "--rm",
                "sleep",
                "/bin/sh",
                "-c",
                "wget -O - http://web:8000/hosts",
            ])
            self.assertIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertIn(b"deps_web_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "down",
            ])

    def test_deps_fails(self) -> None:
        suffix = "-conditional-fails"
        try:
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "ps",
            ])
            self.assertNotIn(b"HTTP request sent, awaiting response... 200 OK", output)
            self.assertNotIn(b"deps_web_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "down",
            ])


class TestComposeConditionalDepsHealthy(unittest.TestCase, PodmanAwareRunSubprocessMixin):
    def setUp(self) -> None:
        self.podman_version = self.retrieve_podman_version()

    @unittest.skipIf(
        get_podman_version() > version.parse("4.4.0"), "Breaks as of podman-4.9.5 and podman-5.4.2."
    )
    def test_up_deps_healthy(self) -> None:
        suffix = "-conditional-healthy"
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "up",
                "sleep",
                "--detach",
            ])

            # Since the command `podman wait --condition=healthy` is invalid prior to 4.6.0,
            # we only validate healthy status for podman 4.6.0+, which won't be tested in the
            # CI pipeline of the podman-compose project where podman 4.3.1 is employed.
            podman_ver_major, podman_ver_minor, podman_ver_patch = self.podman_version
            if podman_ver_major >= 4 and podman_ver_minor >= 6 and podman_ver_patch >= 0:
                self.run_subprocess_assert_returncode([
                    "podman",
                    "wait",
                    "--condition=running",
                    "deps_web_1",
                    "deps_sleep_1",
                ])

            # check both web and sleep are running
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "ps",
                "--format",
                "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.StartedAt}}",
            ])

            # extract container id of web
            decoded_out = output.decode('utf-8')
            lines = decoded_out.split("\n")

            web_lines = [line for line in lines if "web" in line]
            self.assertTrue(web_lines)
            self.assertEqual(1, len(web_lines))
            web_cnt_id, web_cnt_name, web_cnt_status, web_cnt_started = web_lines[0].split("\t")
            self.assertNotEqual("", web_cnt_id)
            self.assertEqual("deps_web_1", web_cnt_name)

            sleep_lines = [line for line in lines if "sleep" in line]
            self.assertTrue(sleep_lines)
            self.assertEqual(1, len(sleep_lines))
            sleep_cnt_id, sleep_cnt_name, _, sleep_cnt_started = sleep_lines[0].split("\t")
            self.assertNotEqual("", sleep_cnt_id)
            self.assertEqual("deps_sleep_1", sleep_cnt_name)

            # When test case is executed inside container like github actions, the absence of
            # systemd prevents health check from working properly, resulting in failure to
            # transit to healthy state. As a result, we only assert the `healthy` state where
            # systemd is functioning.
            if (
                is_systemd_available()
                and podman_ver_major >= 4
                and podman_ver_minor >= 6
                and podman_ver_patch >= 0
            ):
                self.assertIn("healthy", web_cnt_status)
            self.assertGreaterEqual(int(sleep_cnt_started), int(web_cnt_started))

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(suffix),
                "down",
            ])
