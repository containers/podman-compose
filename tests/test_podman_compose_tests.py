"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""
# pylint: disable=redefined-outer-name
import os
import time

from test_podman_compose import capture


def test_exit_from(podman_compose_path, test_path):
    up_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "exit-from", "docker-compose.yaml"),
        "up"
    ]

    out, _, return_code = capture(up_cmd + ["--exit-code-from", "sh1"])
    assert return_code == 1

    out, _, return_code = capture(up_cmd + ["--exit-code-from", "sh2"])
    assert return_code == 2


def test_run(podman_compose_path, test_path):
    """
    This will test depends_on as well
    """
    run_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "deps", "docker-compose.yaml"),
        "run",
        "--rm",
        "sleep",
        "/bin/sh",
        "-c",
        "wget -q -O - http://web:8000/hosts"
    ]

    out, _, return_code = capture(run_cmd)
    assert b'127.0.0.1\tlocalhost' in out

    # Run it again to make sure we can run it twice. I saw an issue where a second run, with the container left up,
    # would fail
    run_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "deps", "docker-compose.yaml"),
        "run",
        "--rm",
        "sleep",
        "/bin/sh",
        "-c",
        "wget -q -O - http://web:8000/hosts"
    ]

    out, _, return_code = capture(run_cmd)
    assert b'127.0.0.1\tlocalhost' in out
    assert return_code == 0

    # This leaves a container running. Not sure it's intended, but it matches docker-compose
    down_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "deps", "docker-compose.yaml"),
        "down",
    ]

    out, _, return_code = capture(run_cmd)
    assert return_code == 0


def test_up_with_ports(podman_compose_path, test_path):


    up_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "ports", "docker-compose.yml"),
        "up",
        "-d",
        "--force-recreate"
    ]

    down_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "ports", "docker-compose.yml"),
        "down",
        "--volumes"
    ]

    try:
        out, _, return_code = capture(up_cmd)
        assert return_code == 0


    finally:
        out, _, return_code = capture(down_cmd)
        assert return_code == 0


def test_down_with_vols(podman_compose_path, test_path):

    up_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "vol", "docker-compose.yaml"),
        "up",
        "-d"
    ]

    down_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "vol", "docker-compose.yaml"),
        "down",
        "--volumes"
    ]

    try:
        out, _, return_code = capture(["podman", "volume", "create", "my-app-data"])
        assert return_code == 0
        out, _, return_code = capture(["podman", "volume", "create", "actual-name-of-volume"])
        assert return_code == 0

        out, _, return_code = capture(up_cmd)
        assert return_code == 0

        capture(["podman", "inspect", "volume", ""])

    finally:
        out, _, return_code = capture(down_cmd)
        capture(["podman", "volume", "rm", "my-app-data"])
        capture(["podman", "volume", "rm", "actual-name-of-volume"])
        assert return_code == 0


def test_down_with_orphans(podman_compose_path, test_path):

    container_id, _ , return_code = capture(["podman", "run", "--rm", "-d", "busybox", "/bin/busybox", "httpd", "-f", "-h", "/etc/", "-p", "8000"])

    down_cmd = [
        "coverage",
        "run",
        podman_compose_path,
        "-f",
        os.path.join(test_path, "ports", "docker-compose.yml"),
        "down",
        "--volumes",
        "--remove-orphans"
    ]

    out, _, return_code = capture(down_cmd)
    assert return_code == 0

    _, _, exists = capture(["podman", "container", "exists", container_id.decode("utf-8")])

    assert exists == 1

