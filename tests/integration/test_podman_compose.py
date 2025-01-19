# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from pathlib import Path


def base_path():
    """Returns the base path for the project"""
    return Path(__file__).parent.parent.parent


def test_path():
    """Returns the path to the tests directory"""
    return os.path.join(base_path(), "tests/integration")


def podman_compose_path():
    """Returns the path to the podman compose script"""
    return os.path.join(base_path(), "podman_compose.py")
