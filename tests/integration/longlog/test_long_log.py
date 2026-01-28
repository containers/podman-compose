# SPDX-License-Identifier: GPL-2.0

import os
import unittest
import uuid

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    base_path = os.path.join(test_path(), "longlog")
    return os.path.join(base_path, "docker-compose-multibyte.yml")


class TestLongLog(unittest.TestCase, RunSubprocessMixin):
    def test_print_until_end_of_multibyte_output(self) -> None:
        # adding uuid because hangup containers can interfere next test runs
        project_id = f"longlog_{uuid.uuid4().hex[:8]}"
        try:
            out, err = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "-p",
                    project_id,
                    "-f",
                    compose_yaml_path(),
                    "up",
                ],
                0,
                timeout=6.0,
            )
            self.assertEqual(b"", err)
            outstring = out.decode("utf-8")
            self.assertTrue(
                outstring.endswith(" end\n"), f"ending with {outstring[-20:].encode('utf-8')!r}"
            )
        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-p",
                project_id,
                "-f",
                compose_yaml_path(),
                "down",
            ])
