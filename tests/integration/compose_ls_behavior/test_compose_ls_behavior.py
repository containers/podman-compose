import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path() -> str:
    return os.path.join(os.path.join(test_path(), "compose_ls_behavior"), "docker-compose.yml")


class TestPodmanComposeLsBehavior(unittest.TestCase, RunSubprocessMixin):
    def test_compose_list(self) -> None:
        path = compose_yaml_path()
        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path,
                "up",
                "-d",
            ])

            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path,
                "ls",
            ])

            result = (
                f'NAME                           \tSTATUS    \tCONFIG_FILES\n'
                f'compose_ls_behavior_service_1_1\trunning(1)\t{path}\n'
                f'compose_ls_behavior_service_2_1\trunning(1)\t{path}\n'
                f'compose_ls_behavior_service_3_1\trunning(1)\t{path}\n'
            ).encode()
            self.assertEqual(result, out)

            # Test for json view
            out, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path,
                "ls",
                "--format",
                "json",
            ])

            result = (
                f"[{{'Name': 'compose_ls_behavior_service_1_1', 'Status': 'running(1)', "
                f"'ConfigFiles': '{path}'}}, "
                f"{{'Name': 'compose_ls_behavior_service_2_1', 'Status': 'running(1)', "
                f"'ConfigFiles': '{path}'}}, "
                f"{{'Name': 'compose_ls_behavior_service_3_1', 'Status': 'running(1)', "
                f"'ConfigFiles': '{path}'}}]\n"
            ).encode()
            self.assertEqual(result, out)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                path,
                "down",
                "-t",
                "0",
            ])
