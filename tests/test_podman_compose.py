from pathlib import Path
import subprocess


def capture(command):
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate()
    return out, err, proc.returncode

def test_podman_compose_extends_w_file_subdir():
    """
    Test that podman-compose can execute podman-compose -f <file> up with extended File which
    includes a build context
    :return:
    """
    main_path = Path(__file__).parent.parent

    command_up = [
        "python3",
        str(main_path.joinpath("podman_compose.py")),
        "-f",
        str(main_path.joinpath("tests", "extends_w_file_subdir", "docker-compose.yml")),
        "up",
        "-d"
    ]

    command_check_container = [
        "podman",
        "container",
        "ps",
        "--all",
        "--format",
        "\"{{.Image}}\""
    ]

    command_down = [
        "podman",
        "rmi",
        "--force",
        "localhost/subdir_test:me",
        "docker.io/library/bash"
    ]

    out, err, returncode = capture(command_up)
    assert 0 == returncode
    # check container was created and exists
    out, err, returncode = capture(command_check_container)
    assert 0 == returncode
    assert out == b'"localhost/subdir_test:me"\n'
    out, err, returncode = capture(command_down)
    # cleanup test image(tags)
    assert 0 == returncode
    # check container did not exists anymore
    out, err, returncode = capture(command_check_container)
    assert 0 == returncode
    assert out == b''
