import pytest

from podman_compose import parse_short_mount

@pytest.fixture
def multi_propagation_mount_str():
    return "/foo/bar:/baz:U,Z"


def test_parse_short_mount_multi_propagation(multi_propagation_mount_str):
    expected = {
        "type": "bind",
        "source": "/foo/bar",
        "target": "/baz",
        "bind": {
            "propagation": "U,Z",
        },
    }
    assert parse_short_mount(multi_propagation_mount_str, "/") == expected
