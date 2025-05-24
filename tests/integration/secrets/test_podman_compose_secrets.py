# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from subprocess import PIPE
from subprocess import Popen

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "secrets"), "docker-compose.yaml")


class TestComposeNoSecrets(unittest.TestCase, RunSubprocessMixin):
    created_secrets = [
        "podman_compose_test_secret",
        "podman_compose_test_secret_2",
        "podman_compose_test_secret_3",
        "podman_compose_test_secret_custom_name",
    ]

    def setUp(self) -> None:
        for secret in self.created_secrets:
            p = Popen(["podman", "secret", "create", secret, "-"], stdin=PIPE)
            p.communicate(secret.encode('utf-8'))

    def tearDown(self) -> None:
        for secret in self.created_secrets:
            self.run_subprocess_assert_returncode([
                "podman",
                "secret",
                "rm",
                f"{secret}",
            ])

    # test if secrets are saved and available in respective files of a container
    def test_secrets(self) -> None:
        try:
            _, error, _ = self.run_subprocess(
                [
                    podman_compose_path(),
                    "-f",
                    compose_yaml_path(),
                    "up",
                    "test",
                ],
            )

            self.assertIn(
                b'WARNING: Service "test" uses target: "podman_compose_test_secret_3" '
                + b'for secret: "podman_compose_test_secret_3". That is un-supported and '
                + b'a no-op and is ignored.',
                error,
            )
            self.assertIn(
                b'WARNING: Service test uses secret unused_params_warning with uid, '
                + b'gid, or mode. These fields are not supported by this implementation '
                + b'of the Compose file',
                error,
            )

            output, _ = self.run_subprocess_assert_returncode(["podman", "logs", "secrets_test_1"])
            expected_output = (
                b'/run/secrets/custom_name:important-secret-is-important\n'
                + b'/run/secrets/file_secret:important-secret-is-important\n'
                + b'/run/secrets/podman_compose_test_secret:podman_compose_test_secret\n'
                + b'/run/secrets/podman_compose_test_secret_3:podman_compose_test_secret_3\n'
                + b'/run/secrets/unused_params_warning:important-secret-is-important\n'
                + b'important-secret-is-important\n'
                + b'podman_compose_test_secret\n'
            )
            self.assertEqual(expected_output, output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(),
                "down",
                "-t",
                "0",
            ])
