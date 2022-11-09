"""conftest.py

Defines global pytest fixtures available to all tests.
"""
import pytest
from pathlib import Path
import os


@pytest.fixture
def base_path():
    """Returns the base path for the project"""
    return Path(__file__).parent.parent


@pytest.fixture
def test_path(base_path):
    """Returns the path to the tests directory"""
    return os.path.join(base_path, "tests")


@pytest.fixture
def podman_compose_path(base_path):
    """Returns the path to the podman compose script"""
    return os.path.join(base_path, "podman_compose.py")
