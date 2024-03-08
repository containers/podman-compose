from pathlib import Path
import subprocess
import unittest


def run_subprocess(command):
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate()
    return out, err, proc.returncode


class TestPodmanComposeInclude(unittest.TestCase):
    def test_podman_compose_include(self):
        """
        Test that podman-compose can execute podman-compose -f <file> up with include
        :return:
        """
        main_path = Path(__file__).parent.parent

        command_up = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "include", "docker-compose.yaml")),
            "up",
            "-d",
        ]

        command_check_container = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=include",
            "--format",
            '"{{.Image}}"',
        ]

        command_container_id = [
            "podman",
            "ps",
            "-a",
            "--filter",
            "label=io.podman.compose.project=include",
            "--format",
            '"{{.ID}}"',
        ]

        command_down = ["podman", "rm", "--force", "CONTAINER_ID"]

        out, _, returncode = run_subprocess(command_up)
        self.assertEqual(returncode, 0)
        out, _, returncode = run_subprocess(command_check_container)
        self.assertEqual(returncode, 0)
        self.assertEqual(out, b'"docker.io/library/busybox:latest"\n')
        # Get container ID to remove it
        out, _, returncode = run_subprocess(command_container_id)
        self.assertEqual(returncode, 0)
        self.assertNotEqual(out, b"")
        container_id = out.decode().strip().replace('"', "")
        command_down[3] = container_id
        out, _, returncode = run_subprocess(command_down)
        # cleanup test image(tags)
        self.assertEqual(returncode, 0)
        self.assertNotEqual(out, b"")
        # check container did not exists anymore
        out, _, returncode = run_subprocess(command_check_container)
        self.assertEqual(returncode, 0)
        self.assertEqual(out, b"")
