"""
test_podman_compose_config.py

Tests the podman-compose config command which is used to return defined compose services.
"""
import pytest
import os
from test_podman_compose import capture


@pytest.fixture
def profile_compose_file(test_path):
    """ "Returns the path to the `profile` compose file used for this test module"""
    return os.path.join(test_path, "profile", "docker-compose.yml")


def test_config_no_profiles(podman_compose_path, profile_compose_file):
    """
    Tests podman-compose config command without profile enablement.

    :param podman_compose_path: The fixture used to specify the path to the podman compose file.
    :param profile_compose_file: The fixtued used to specify the path to the "profile" compose used in the test.
    """
    config_cmd = ["python3", podman_compose_path, "-f", profile_compose_file, "config"]

    out, err, return_code = capture(config_cmd)
    assert return_code == 0

    string_output = out.decode("utf-8")
    assert "default-service" in string_output
    assert "service-1" not in string_output
    assert "service-2" not in string_output


@pytest.mark.parametrize(
    "profiles, expected_services",
    [
        (
            ["--profile", "profile-1", "config"],
            {"default-service": True, "service-1": True, "service-2": False},
        ),
        (
            ["--profile", "profile-2", "config"],
            {"default-service": True, "service-1": False, "service-2": True},
        ),
        (
            ["--profile", "profile-1", "--profile", "profile-2", "config"],
            {"default-service": True, "service-1": True, "service-2": True},
        ),
    ],
)
def test_config_profiles(
    podman_compose_path, profile_compose_file, profiles, expected_services
):
    """
    Tests podman-compose
    :param podman_compose_path: The fixture used to specify the path to the podman compose file.
    :param profile_compose_file: The fixtued used to specify the path to the "profile" compose used in the test.
    :param profiles: The enabled profiles for the parameterized test.
    :param expected_services: Dictionary used to model the expected "enabled" services in the profile.
        Key = service name, Value = True if the service is enabled, otherwise False.
    """
    config_cmd = ["python3", podman_compose_path, "-f", profile_compose_file]
    config_cmd.extend(profiles)

    out, err, return_code = capture(config_cmd)
    assert return_code == 0

    actual_output = out.decode("utf-8")

    assert len(expected_services) == 3

    actual_services = {}
    for service, expected_check in expected_services.items():
        actual_services[service] = service in actual_output

    assert expected_services == actual_services
