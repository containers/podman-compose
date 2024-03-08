from pathlib import Path
import subprocess
import os
import unittest


def run_subprocess(command):
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate()
    return out, err, proc.returncode


def base_path():
    """Returns the base path for the project"""
    return Path(__file__).parent.parent


def test_path():
    """Returns the path to the tests directory"""
    return os.path.join(base_path(), "tests")


def podman_compose_path():
    """Returns the path to the podman compose script"""
    return os.path.join(base_path(), "podman_compose.py")


class TestPodmanCompose(unittest.TestCase):
    def test_extends_w_file_subdir(self):
        """
        Test that podman-compose can execute podman-compose -f <file> up with extended File which
        includes a build context
        :return:
        """
        main_path = Path(__file__).parent.parent

        command_up = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "extends_w_file_subdir", "docker-compose.yml")),
            "up",
            "-d",
        ]

        command_check_container = [
            "coverage",
            "run",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "extends_w_file_subdir", "docker-compose.yml")),
            "ps",
            "--format",
            '{{.Image}}',
        ]

        command_down = [
            "podman",
            "rmi",
            "--force",
            "localhost/subdir_test:me",
            "docker.io/library/busybox",
        ]

        out, _, returncode = run_subprocess(command_up)
        self.assertEqual(returncode, 0)
        # check container was created and exists
        out, err, returncode = run_subprocess(command_check_container)
        self.assertEqual(returncode, 0)
        self.assertEqual(out, b'localhost/subdir_test:me\n')
        out, _, returncode = run_subprocess(command_down)
        # cleanup test image(tags)
        self.assertEqual(returncode, 0)
        # check container did not exists anymore
        out, _, returncode = run_subprocess(command_check_container)
        self.assertEqual(returncode, 0)
        self.assertEqual(out, b'')

    def test_extends_w_empty_service(self):
        """
        Test that podman-compose can execute podman-compose -f <file> up with extended File which
        includes an empty service. (e.g. if the file is used as placeholder for more complex configurations.)
        :return:
        """
        main_path = Path(__file__).parent.parent

        command_up = [
            "python3",
            str(main_path.joinpath("podman_compose.py")),
            "-f",
            str(main_path.joinpath("tests", "extends_w_empty_service", "docker-compose.yml")),
            "up",
            "-d",
        ]

        _, _, returncode = run_subprocess(command_up)
        self.assertEqual(returncode, 0)
