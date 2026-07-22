# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(scenario: str) -> str:
    return os.path.join(
        os.path.join(test_path(), "invalid_secrets_dict"), f"docker-compose_{scenario}.yaml"
    )


class TestComposeInvalidSecretsDict(unittest.TestCase, RunSubprocessMixin):
    def test_invalid_service_secrets_dict_fails(self) -> None:
        _, err = self.run_subprocess_assert_returncode(
            [podman_compose_path(), "-f", compose_yaml_path("service"), "config"], 1
        )
        self.assertIn(b"ERROR: secrets must be a list, not a dict", err)
