from pathlib import Path

from utils import capture


def test_podman_compose_include():
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

    out, _, returncode = capture(command_up)
    assert 0 == returncode
    out, _, returncode = capture(command_check_container)
    assert 0 == returncode
    assert out == b'"docker.io/library/busybox:latest"\n'
    # Get container ID to remove it
    out, _, returncode = capture(command_container_id)
    assert 0 == returncode
    assert out != b""
    container_id = out.decode().strip().replace('"', "")
    command_down[3] = container_id
    out, _, returncode = capture(command_down)
    # cleanup test image(tags)
    assert 0 == returncode
    assert out != b""
    # check container did not exists anymore
    out, _, returncode = capture(command_check_container)
    assert 0 == returncode
    assert out == b""
