# SPDX-License-Identifier: GPL-2.0

import unittest

from parameterized import parameterized

from podman_compose import is_path_git_url


class TestIsPathGitUrl(unittest.TestCase):
    @parameterized.expand([
        ("prefix_git", "git://host.xz/path/to/repo", True),
        ("prefix_almost_git", "gitt://host.xz/path/to/repo", False),
        ("prefix_wrong", "http://host.xz/path/to/repo", False),
        ("suffix_git", "http://host.xz/path/to/repo.git", True),
        ("suffix_wrong", "http://host.xz/path/to/repo", False),
        ("suffix_with_url_fragment", "http://host.xz/path/to/repo.git#fragment", True),
        ("suffix_and_prefix", "git://host.xz/path/to/repo.git", True),
        ("empty_url_path", "http://#fragment", False),
    ])
    def test_is_path_git_url(self, test_name, path, result):
        self.assertEqual(is_path_git_url(path), result)
