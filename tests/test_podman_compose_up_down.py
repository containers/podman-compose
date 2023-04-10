"""
test_podman_compose_up_down.py

Tests the podman compose up and down commands used to create and remove services.
"""
import pytest
import os
from test_podman_compose import capture


@pytest.fixture
def profile_compose_file(test_path):
    """ "Returns the path to the `profile` compose file used for this test module"""
    return os.path.join(test_path, "profile", "docker-compose.yml")


@pytest.fixture(autouse=True)
def teardown(podman_compose_path, profile_compose_file):
    """
    Ensures that the services within the "profile compose file" are removed between each test case.

    :param podman_compose_path: The path to the podman compose script.
    :param profile_compose_file: The path to the compose file used for this test module.
    """
    # run the test case
    yield

    down_cmd = [
        "python3",
        podman_compose_path,
        "--profile",
        "profile-1",
        "--profile",
        "profile-2",
        "-f",
        profile_compose_file,
        "down",
    ]
    capture(down_cmd)


@pytest.mark.parametrize(
    "profiles, expected_services",
    [
        (
            ["--profile", "profile-1", "up", "-d"],
            {"default-service": True, "service-1": True, "service-2": False},
        ),
        (
            ["--profile", "profile-2", "up", "-d"],
            {"default-service": True, "service-1": False, "service-2": True},
        ),
        (
            ["--profile", "profile-1", "--profile", "profile-2", "up", "-d"],
            {"default-service": True, "service-1": True, "service-2": True},
        ),
    ],
)
def test_up(podman_compose_path, profile_compose_file, profiles, expected_services):
    up_cmd = [
        "python3",
        podman_compose_path,
        "-f",
        profile_compose_file,
    ]
    up_cmd.extend(profiles)

    out, err, return_code = capture(up_cmd)
    assert return_code == 0

    check_cmd = [
        "podman",
        "container",
        "ps",
        "--format",
        '"{{.Names}}"',
    ]
    out, err, return_code = capture(check_cmd)
    assert return_code == 0

    assert len(expected_services) == 3
    actual_output = out.decode("utf-8")

    actual_services = {}
    for service, expected_check in expected_services.items():
        actual_services[service] = service in actual_output

    assert expected_services == actual_services
