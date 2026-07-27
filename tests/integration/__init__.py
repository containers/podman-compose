import os
import subprocess


def create_base_test_image() -> None:
    base_image_dir = os.path.join(os.path.dirname(__file__), "base_image")
    subprocess.check_call(
        ['podman', 'build', '-t', 'nopush/podman-compose-test', '.'],
        cwd=base_image_dir,
    )
    subprocess.check_call(
        ['podman', 'build', '-t', 'nopush/podman-compose-test2', '-f', 'Dockerfile.test2', '.'],
        cwd=base_image_dir,
    )


create_base_test_image()
