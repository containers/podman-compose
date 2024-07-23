# SPDX-License-Identifier: GPL-2.0

import os
import unittest
from unittest import mock

from parameterized import parameterized

from podman_compose import container_to_args


def create_compose_mock(project_name="test_project_name"):
    compose = mock.Mock()
    compose.project_name = project_name
    compose.dirname = "test_dirname"
    compose.container_names_by_service.get = mock.Mock(return_value=None)
    compose.prefer_volume_over_mount = False
    compose.default_net = None
    compose.networks = {}
    compose.x_podman = {}

    async def podman_output(*args, **kwargs):
        pass

    compose.podman.output = mock.Mock(side_effect=podman_output)
    return compose


def get_minimal_container():
    return {
        "name": "project_name_service_name1",
        "service_name": "service_name",
        "image": "busybox",
    }


def get_test_file_path(rel_path):
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.realpath(os.path.join(repo_root, rel_path))


class TestContainerToArgs(unittest.IsolatedAsyncioTestCase):
    async def test_minimal(self):
        c = create_compose_mock()

        cnt = get_minimal_container()

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    async def test_runtime(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["runtime"] = "runsc"

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--runtime",
                "runsc",
                "busybox",
            ],
        )

    async def test_sysctl_list(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["sysctls"] = [
            "net.core.somaxconn=1024",
            "net.ipv4.tcp_syncookies=0",
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--sysctl",
                "net.core.somaxconn=1024",
                "--sysctl",
                "net.ipv4.tcp_syncookies=0",
                "busybox",
            ],
        )

    async def test_sysctl_map(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["sysctls"] = {
            "net.core.somaxconn": 1024,
            "net.ipv4.tcp_syncookies": 0,
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--sysctl",
                "net.core.somaxconn=1024",
                "--sysctl",
                "net.ipv4.tcp_syncookies=0",
                "busybox",
            ],
        )

    async def test_sysctl_wrong_type(self):
        c = create_compose_mock()
        cnt = get_minimal_container()

        # check whether wrong types are correctly rejected
        for wrong_type in [True, 0, 0.0, "wrong", ()]:
            with self.assertRaises(TypeError):
                cnt["sysctls"] = wrong_type
                await container_to_args(c, cnt)

    async def test_pid(self):
        c = create_compose_mock()
        cnt = get_minimal_container()

        cnt["pid"] = "host"

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--pid",
                "host",
                "busybox",
            ],
        )

    async def test_http_proxy(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["http_proxy"] = False

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--http-proxy=false",
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    async def test_uidmaps_extension_old_path(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['x-podman'] = {'uidmaps': ['1000:1000:1']}

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    async def test_uidmaps_extension(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['x-podman.uidmaps'] = ['1000:1000:1', '1001:1001:2']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                '--uidmap',
                '1000:1000:1',
                '--uidmap',
                '1001:1001:2',
                "busybox",
            ],
        )

    async def test_gidmaps_extension(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['x-podman.gidmaps'] = ['1000:1000:1', '1001:1001:2']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                '--gidmap',
                '1000:1000:1',
                '--gidmap',
                '1001:1001:2',
                "busybox",
            ],
        )

    async def test_rootfs_extension(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        del cnt["image"]
        cnt["x-podman.rootfs"] = "/path/to/rootfs"

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--rootfs",
                "/path/to/rootfs",
            ],
        )

    async def test_env_file_str(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env-file-tests/env-files/project-1.env')
        cnt['env_file'] = env_file

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "-e",
                "ZZVAR1=podman-rocks-123",
                "-e",
                "ZZVAR2=podman-rocks-124",
                "-e",
                "ZZVAR3=podman-rocks-125",
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_str_not_exists(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['env_file'] = 'notexists'

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    async def test_env_file_str_array_one_path(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env-file-tests/env-files/project-1.env')
        cnt['env_file'] = [env_file]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "-e",
                "ZZVAR1=podman-rocks-123",
                "-e",
                "ZZVAR2=podman-rocks-124",
                "-e",
                "ZZVAR3=podman-rocks-125",
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_str_array_two_paths(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env-file-tests/env-files/project-1.env')
        env_file_2 = get_test_file_path('tests/integration/env-file-tests/env-files/project-2.env')
        cnt['env_file'] = [env_file, env_file_2]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "-e",
                "ZZVAR1=podman-rocks-123",
                "-e",
                "ZZVAR2=podman-rocks-124",
                "-e",
                "ZZVAR3=podman-rocks-125",
                "-e",
                "ZZVAR1=podman-rocks-223",
                "-e",
                "ZZVAR2=podman-rocks-224",
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_obj_required(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env-file-tests/env-files/project-1.env')
        cnt['env_file'] = {'path': env_file, 'required': True}

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "-e",
                "ZZVAR1=podman-rocks-123",
                "-e",
                "ZZVAR2=podman-rocks-124",
                "-e",
                "ZZVAR3=podman-rocks-125",
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_obj_required_non_existent_path(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['env_file'] = {'path': 'not-exists', 'required': True}

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    async def test_env_file_obj_optional(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['env_file'] = {'path': 'not-exists', 'required': False}

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    async def test_gpu_count_all(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["command"] = ["nvidia-smi"]
        cnt["deploy"] = {"resources": {"reservations": {"devices": [{}]}}}

        cnt["deploy"]["resources"]["reservations"]["devices"][0] = {
            "driver": "nvidia",
            "count": "all",
            "capabilities": ["gpu"],
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--device",
                "nvidia.com/gpu=all",
                "--security-opt=label=disable",
                "busybox",
                "nvidia-smi",
            ],
        )

    async def test_gpu_count_specific(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["command"] = ["nvidia-smi"]
        cnt["deploy"] = {
            "resources": {
                "reservations": {
                    "devices": [
                        {
                            "driver": "nvidia",
                            "count": 2,
                            "capabilities": ["gpu"],
                        }
                    ]
                }
            }
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--device",
                "nvidia.com/gpu=0",
                "--device",
                "nvidia.com/gpu=1",
                "--security-opt=label=disable",
                "busybox",
                "nvidia-smi",
            ],
        )

    async def test_gpu_device_ids_all(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["command"] = ["nvidia-smi"]
        cnt["deploy"] = {
            "resources": {
                "reservations": {
                    "devices": [
                        {
                            "driver": "nvidia",
                            "device_ids": "all",
                            "capabilities": ["gpu"],
                        }
                    ]
                }
            }
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--device",
                "nvidia.com/gpu=all",
                "--security-opt=label=disable",
                "busybox",
                "nvidia-smi",
            ],
        )

    async def test_gpu_device_ids_specific(self):
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["command"] = ["nvidia-smi"]
        cnt["deploy"] = {
            "resources": {
                "reservations": {
                    "devices": [
                        {
                            "driver": "nvidia",
                            "device_ids": [1, 3],
                            "capabilities": ["gpu"],
                        }
                    ]
                }
            }
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--device",
                "nvidia.com/gpu=1",
                "--device",
                "nvidia.com/gpu=3",
                "--security-opt=label=disable",
                "busybox",
                "nvidia-smi",
            ],
        )

    @parameterized.expand([
        (False, "z", ["--mount", "type=bind,source=./foo,destination=/mnt,z"]),
        (False, "Z", ["--mount", "type=bind,source=./foo,destination=/mnt,Z"]),
        (True, "z", ["-v", "./foo:/mnt:z"]),
        (True, "Z", ["-v", "./foo:/mnt:Z"]),
    ])
    async def test_selinux_volume(self, prefer_volume, selinux_type, expected_additional_args):
        c = create_compose_mock()
        c.prefer_volume_over_mount = prefer_volume

        cnt = get_minimal_container()

        # This is supposed to happen during `_parse_compose_file`
        # but that is probably getting skipped during testing
        cnt["_service"] = cnt["service_name"]

        cnt["volumes"] = [
            {
                "type": "bind",
                "source": "./foo",
                "target": "/mnt",
                "bind": {
                    "selinux": selinux_type,
                },
            }
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                *expected_additional_args,
                "--network=bridge",
                "--network-alias=service_name",
                "busybox",
            ],
        )

    @parameterized.expand([
        ("not_compat", False, "test_project_name", "test_project_name_network1"),
        ("compat_no_dash", True, "test_project_name", "test_project_name_network1"),
        ("compat_dash", True, "test_project-name", "test_projectname_network1"),
    ])
    async def test_network_default_name(self, name, is_compat, project_name, expected_network_name):
        c = create_compose_mock(project_name)
        c.x_podman = {"default_net_name_compat": is_compat}
        c.networks = {'network1': {}}

        cnt = get_minimal_container()
        cnt['networks'] = ['network1']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                f"--network={expected_network_name}",
                "--network-alias=service_name",
                "busybox",
            ],
        )
