# SPDX-License-Identifier: GPL-2.0

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
                './Containerfile',
                '-t',
                'new-image',
                '--no-cache',
                '--pull-always',
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
                './Containerfile',
                '-t',
                'new-image',
                '--platform',
                'linux/amd64',
                '--no-cache',
                '--pull-always',
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
                './Containerfile',
                '-t',
                'new-image',
                '-t',
                'some-tag1',
                '-t',
                'some-tag2:2',
                '--no-cache',
                '--pull-always',
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
                './Containerfile',
                '-t',
                'new-image',
                '--label',
                'some-label1',
                '--label',
                'some-label2.2',
                '--no-cache',
                '--pull-always',
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
                './Containerfile',
                '-t',
                'new-image',
                '--no-cache',
                '--pull-always',
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
