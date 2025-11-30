import ast
import os
import unittest

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


class TestPodmanComposeInclude(unittest.TestCase, RunSubprocessMixin):
    def test_podman_compose_list(self) -> None:
        """
        Test podman compose list (ls) command
        """
        command_up = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "list", "docker-compose.yml"),
            "up",
            "-d",
        ]

        command_list = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            os.path.join(test_path(), "list", "docker-compose.yml"),
            "ls",
        ]

        command_check_container = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=list",
            "--format",
            '"{{.Image}}"',
        ]

        command_container_id = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=list",
            "--format",
            '"{{.ID}}"',
        ]

        command_down = ["podman", "rm", "--force"]

        running_containers = []
        self.run_subprocess_assert_returncode(command_up)
        out, _ = self.run_subprocess_assert_returncode(command_list)
        out = out.decode()

        # Test for table view
        services = out.strip().split("\n")
        headers = [h.strip() for h in services[0].split("\t")]

        for service in services[1:]:
            values = [val.strip() for val in service.split("\t")]
            zipped = dict(zip(headers, values))
            self.assertNotEqual(zipped.get("NAME"), None)
            self.assertNotEqual(zipped.get("STATUS"), None)
            self.assertNotEqual(zipped.get("CONFIG_FILES"), None)
            running_containers.append(zipped)
        self.assertEqual(len(running_containers), 3)

        # Test for json view
        command_list.extend(["--format", "json"])
        out, _ = self.run_subprocess_assert_returncode(command_list)
        out = out.decode()
        services = ast.literal_eval(out)

        for service in services:
            self.assertIsInstance(service, dict)
            self.assertNotEqual(service.get("Name"), None)
            self.assertNotEqual(service.get("Status"), None)
            self.assertNotEqual(service.get("ConfigFiles"), None)

        self.assertEqual(len(services), 3)

        # Get container ID to remove it
        out, _ = self.run_subprocess_assert_returncode(command_container_id)
        self.assertNotEqual(out, b"")
        container_ids = out.decode().strip().split("\n")
        container_ids = [container_id.replace('"', "") for container_id in container_ids]
        command_down.extend(container_ids)
        out, _ = self.run_subprocess_assert_returncode(command_down)
        # cleanup test image(tags)
        self.assertNotEqual(out, b"")
        # check container did not exists anymore
        out, _ = self.run_subprocess_assert_returncode(command_check_container)
        self.assertEqual(out, b"")
