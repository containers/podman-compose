# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from unittest import mock

from podman_compose import container_to_build_args


def create_compose_mock(project_name='test_project_name'):
    compose = mock.Mock()
    compose.project_name = project_name
    compose.dirname = 'test_dirname'
    compose.container_names_by_service.get = mock.Mock(return_value=None)
    compose.prefer_volume_over_mount = False
    compose.default_net = None
    compose.networks = {}
    compose.x_podman = {}
    return compose


def get_minimal_container():
    return {
        'name': 'project_name_service_name1',
        'service_name': 'service_name',
        'image': 'new-image',
        'build': {},
    }


def get_minimal_args():
    args = mock.Mock()
    args.build_arg = []
    args.pull = None
    return args


class TestContainerToBuildArgs(unittest.TestCase):
    def test_minimal(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--no-cache',
                '.',
            ],
        )

    def test_platform(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['platform'] = 'linux/amd64'
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--platform',
                'linux/amd64',
                '--no-cache',
                '.',
            ],
        )

    def test_tags(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['tags'] = ['some-tag1', 'some-tag2:2']
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '-t',
                'some-tag1',
                '-t',
                'some-tag2:2',
                '--no-cache',
                '.',
            ],
        )

    def test_labels(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['labels'] = ['some-label1', 'some-label2.2']
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--label',
                'some-label1',
                '--label',
                'some-label2.2',
                '--no-cache',
                '.',
            ],
        )

    def test_caches(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['cache_from'] = ['registry/image1', 'registry/image2']
        cnt['build']['cache_to'] = ['registry/image3', 'registry/image4']
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--no-cache',
                '--cache-from',
                'registry/image1',
                '--cache-from',
                'registry/image2',
                '--cache-to',
                'registry/image3',
                '--cache-to',
                'registry/image4',
                '.',
            ],
        )

    def test_dockerfile_inline(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['dockerfile_inline'] = "FROM busybox\nRUN echo 'hello world'"
        args = get_minimal_args()

        cleanup_callbacks = []
        args = container_to_build_args(
            c, cnt, args, lambda path: True, cleanup_callbacks=cleanup_callbacks
        )

        temp_dockerfile = args[args.index("-f") + 1]
        self.assertTrue(os.path.exists(temp_dockerfile))

        with open(temp_dockerfile) as file:
            contents = file.read()
            self.assertEqual(contents, "FROM busybox\n" + "RUN echo 'hello world'")

        for c in cleanup_callbacks:
            c()
        self.assertFalse(os.path.exists(temp_dockerfile))

    def test_context_git_url(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['context'] = "https://github.com/test_repo.git"
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: False)
        self.assertEqual(
            args,
            [
                '-t',
                'new-image',
                '--no-cache',
                'https://github.com/test_repo.git',
            ],
        )

    def test_context_invalid_git_url_git_is_not_prefix(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['context'] = "not_prefix://github.com/test_repo"
        args = get_minimal_args()

        with self.assertRaises(OSError):
            container_to_build_args(c, cnt, args, lambda path: False)

    def test_build_ssh_absolute_path(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['ssh'] = ["id1=/test1"]
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--ssh',
                'id1=/test1',
                '--no-cache',
                '.',
            ],
        )

    def test_build_ssh_relative_path(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['ssh'] = ["id1=id1/test1"]
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--ssh',
                'id1=test_dirname/id1/test1',
                '--no-cache',
                '.',
            ],
        )

    def test_build_ssh_working_dir(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['ssh'] = ["id1=./test1"]
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--ssh',
                'id1=test_dirname/./test1',
                '--no-cache',
                '.',
            ],
        )

    @mock.patch.dict(os.environ, {"HOME": "/home/user"}, clear=True)
    def test_build_ssh_path_home_dir(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['ssh'] = ["id1=~/test1"]
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--ssh',
                'id1=/home/user/test1',
                '--no-cache',
                '.',
            ],
        )

    def test_build_ssh_map(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['ssh'] = {"id1": "test1", "id2": "test2"}
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--ssh',
                'id1=test_dirname/test1',
                '--ssh',
                'id2=test_dirname/test2',
                '--no-cache',
                '.',
            ],
        )

    def test_build_ssh_array(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['ssh'] = ['id1=test1', 'id2=test2']
        args = get_minimal_args()

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--ssh',
                'id1=test_dirname/test1',
                '--ssh',
                'id2=test_dirname/test2',
                '--no-cache',
                '.',
            ],
        )

    def test_pull_always(self):
        c = create_compose_mock()
        cnt = get_minimal_container()
        args = get_minimal_args()
        args.pull = 'always'

        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'Containerfile',
                '-t',
                'new-image',
                '--no-cache',
                '--pull=always',
                '.',
            ],
        )

    def test_containerfile_in_context(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['build']['context'] = "./subdir"
        args = get_minimal_args()
        args = container_to_build_args(c, cnt, args, lambda path: True)
        self.assertEqual(
            args,
            [
                '-f',
                'subdir/Containerfile',
                '-t',
                'new-image',
                '--no-cache',
                './subdir',
            ],
        )
