# SPDX-License-Identifier: GPL-2.0
import os
import time
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import is_systemd_available
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(suffix=""):
    return os.path.join(os.path.join(test_path(), "deps"), f"docker-compose{suffix}.yaml")


class TestComposeBaseDeps(unittest.TestCase, RunSubprocessMixin):
    def test_deps(self):
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

    def test_run_nodeps(self):
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

    def test_up_nodeps(self):
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

    def test_podman_compose_run(self):
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
    def test_deps_succeeds(self):
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

    def test_deps_fails(self):
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


class TestComposeConditionalDepsHealthy(unittest.TestCase, RunSubprocessMixin):
    def test_up_deps_healthy(self):
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

            # The `podman wait --condition=healthy` is invalid prior to 4.6.0.
            # Since the podman-compose project uses podman 4.3.1 in github actions, we
            # use sleep as workaround to wait until the `sleep` container becomes running.
            time.sleep(3)

            # self.run_subprocess_assert_returncode([
            #     "podman",
            #     "wait",
            #     "--condition=running",
            #     "deps_web_1",
            #     "deps_sleep_1",
            # ])

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
            web_cnt_id = ""
            web_cnt_name = ""
            web_cnt_status = ""
            web_cnt_started = ""
            sleep_cnt_id = ""
            sleep_cnt_name = ""
            sleep_cnt_started = ""
            for line in decoded_out.split("\n"):
                if "web" in line:
                    web_cnt_id, web_cnt_name, web_cnt_status, web_cnt_started = line.split("\t")
                if "sleep" in line:
                    sleep_cnt_id, sleep_cnt_name, _, sleep_cnt_started = line.split("\t")
            self.assertNotEqual("", web_cnt_id)
            self.assertEqual("deps_web_1", web_cnt_name)
            self.assertNotEqual("", sleep_cnt_id)
            self.assertEqual("deps_sleep_1", sleep_cnt_name)

            # When test case is executed inside container like github actions, the absence of
            # systemd prevents health check from working properly, resulting in failure to
            # transit to healthy state. As a result, we only assert the `healthy` state where
            # systemd is functioning.
            if is_systemd_available():
                self.assertIn("healthy", web_cnt_status)
            self.assertGreaterEqual(int(sleep_cnt_started), int(web_cnt_started))

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
            ])
