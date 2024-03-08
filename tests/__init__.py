import os
import subprocess


def create_base_test_image():
    subprocess.check_call(
        ['podman', 'build', '-t', 'nopush/podman-compose-test', '.'],
        cwd=os.path.join(os.path.dirname(__file__), "base_image"),
    )


create_base_test_image()
