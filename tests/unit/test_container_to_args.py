# SPDX-License-Identifier: GPL-2.0

import os
import shutil
import unittest
from typing import Any
from unittest import mock

from parameterized import parameterized

from podman_compose import PodmanCompose
from podman_compose import container_to_args


def create_compose_mock(project_name: str = "test_project_name") -> PodmanCompose:
    compose = mock.Mock()
    compose.project_name = project_name
    compose.dirname = "test_dirname"
    compose.container_names_by_service.get = mock.Mock(return_value=None)
    compose.prefer_volume_over_mount = False
    compose.default_net = None
    compose.networks = {}
    compose.x_podman = {}
    compose.join_name_parts = mock.Mock(side_effect=lambda *args: '_'.join(args))
    compose.format_name = mock.Mock(side_effect=lambda *args: '_'.join([project_name, *args]))

    async def podman_output(*args: Any, **kwargs: Any) -> None:
        pass

    compose.podman.output = mock.Mock(side_effect=podman_output)
    return compose


def get_minimal_container() -> dict[str, Any]:
    return {
        "name": "project_name_service_name1",
        "service_name": "service_name",
        "image": "busybox",
    }


def get_test_file_path(rel_path: str) -> str:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.realpath(os.path.join(repo_root, rel_path))


class TestContainerToArgs(unittest.IsolatedAsyncioTestCase):
    async def test_minimal(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_runtime(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["runtime"] = "runsc"

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--runtime",
                "runsc",
                "busybox",
            ],
        )

    async def test_sysctl_list(self) -> None:
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
                "--network=bridge:alias=service_name",
                "--sysctl",
                "net.core.somaxconn=1024",
                "--sysctl",
                "net.ipv4.tcp_syncookies=0",
                "busybox",
            ],
        )

    async def test_sysctl_map(self) -> None:
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
                "--network=bridge:alias=service_name",
                "--sysctl",
                "net.core.somaxconn=1024",
                "--sysctl",
                "net.ipv4.tcp_syncookies=0",
                "busybox",
            ],
        )

    async def test_sysctl_wrong_type(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()

        # check whether wrong types are correctly rejected
        for wrong_type in [True, 0, 0.0, "wrong", ()]:
            with self.assertRaises(TypeError):
                cnt["sysctls"] = wrong_type
                await container_to_args(c, cnt)

    async def test_pid(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()

        cnt["pid"] = "host"

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--pid",
                "host",
                "busybox",
            ],
        )

    async def test_http_proxy(self) -> None:
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
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_uidmaps_extension_old_path(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['x-podman'] = {'uidmaps': ['1000:1000:1']}

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    async def test_uidmaps_extension(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['x-podman.uidmaps'] = ['1000:1000:1', '1001:1001:2']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                '--uidmap',
                '1000:1000:1',
                '--uidmap',
                '1001:1001:2',
                "busybox",
            ],
        )

    async def test_gidmaps_extension(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['x-podman.gidmaps'] = ['1000:1000:1', '1001:1001:2']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                '--gidmap',
                '1000:1000:1',
                '--gidmap',
                '1001:1001:2',
                "busybox",
            ],
        )

    async def test_cgroup_conf_extension(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['x-podman.cgroup_conf'] = ['memory.high=1000M', 'memory.min=200M']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                '--cgroup-conf',
                'memory.high=1000M',
                '--cgroup-conf',
                'memory.min=200M',
                "busybox",
            ],
        )

    async def test_rootfs_extension(self) -> None:
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
                "--network=bridge:alias=service_name",
                "--rootfs",
                "/path/to/rootfs",
            ],
        )

    async def test_no_hosts_extension(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt["x-podman.no_hosts"] = True

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--no-hosts",
                "busybox",
            ],
        )

    @parameterized.expand([
        # short syntax: only take this specific environment variable value from .env file
        ("use_env_var_from_default_env_file_short_syntax", ["ZZVAR1"], "ZZVAR1=TEST1"),
        # long syntax: environment variable value from .env file is taken through variable
        # interpolation
        # only the value required in 'environment:' compose file is sent to containers
        # environment
        ("use_env_var_from_default_env_file_long_syntax", ["ZZVAR1=TEST1"], "ZZVAR1=TEST1"),
        # "environment:" section in compose file overrides environment variable value from .env file
        (
            "use_env_var_from_default_env_file_override_value",
            ["ZZVAR1=NEW_TEST1"],
            "ZZVAR1=NEW_TEST1",
        ),
    ])
    async def test_env_file(self, test_name: str, cnt_env: list, expected_var: str) -> None:
        c = create_compose_mock()
        # environment variables were set in .env file
        c.environ = {"ZZVAR1": "TEST1", "ZZVAR2": "TEST2"}

        cnt = get_minimal_container()
        cnt["environment"] = cnt_env

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "-e",
                f"{expected_var}",
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_str(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env_file_tests/env-files/project-1.env')
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
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_str_not_exists(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['env_file'] = 'notexists'

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    async def test_env_file_str_array_one_path(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env_file_tests/env-files/project-1.env')
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
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_str_array_two_paths(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env_file_tests/env-files/project-1.env')
        env_file_2 = get_test_file_path('tests/integration/env_file_tests/env-files/project-2.env')
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
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_obj_required(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        env_file = get_test_file_path('tests/integration/env_file_tests/env-files/project-1.env')
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
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_env_file_obj_required_non_existent_path(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['env_file'] = {'path': 'not-exists', 'required': True}

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    async def test_env_file_obj_optional(self) -> None:
        c = create_compose_mock()

        cnt = get_minimal_container()
        cnt['env_file'] = {'path': 'not-exists', 'required': False}

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_gpu_count_all(self) -> None:
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
                "--network=bridge:alias=service_name",
                "--device",
                "nvidia.com/gpu=all",
                "--security-opt=label=disable",
                "busybox",
                "nvidia-smi",
            ],
        )

    async def test_gpu_count_specific(self) -> None:
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
                "--network=bridge:alias=service_name",
                "--device",
                "nvidia.com/gpu=0",
                "--device",
                "nvidia.com/gpu=1",
                "--security-opt=label=disable",
                "busybox",
                "nvidia-smi",
            ],
        )

    async def test_gpu_device_ids_all(self) -> None:
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
                "--network=bridge:alias=service_name",
                "--device",
                "nvidia.com/gpu=all",
                "--security-opt=label=disable",
                "busybox",
                "nvidia-smi",
            ],
        )

    async def test_gpu_device_ids_specific(self) -> None:
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
                "--network=bridge:alias=service_name",
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
        (
            False,
            "z",
            [
                "--mount",
                f"type=bind,source={get_test_file_path('test_dirname/foo')},destination=/mnt,z",
            ],
        ),
        (
            False,
            "Z",
            [
                "--mount",
                f"type=bind,source={get_test_file_path('test_dirname/foo')},destination=/mnt,Z",
            ],
        ),
        (True, "z", ["-v", f"{get_test_file_path('test_dirname/foo')}:/mnt:z"]),
        (True, "Z", ["-v", f"{get_test_file_path('test_dirname/foo')}:/mnt:Z"]),
    ])
    async def test_selinux_volume(
        self, prefer_volume: bool, selinux_type: str, expected_additional_args: list
    ) -> None:
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
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_volumes_glob_mount_source(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()

        # This is supposed to happen during `_parse_compose_file`
        # but that is probably getting skipped during testing
        cnt["_service"] = cnt["service_name"]

        cnt["volumes"] = [
            {
                "type": "glob",
                "source": f"{get_test_file_path('test_dirname/foo')}/*.ext",
                "target": "/mnt",
            }
        ]
        expected_additional_args = [
            "--mount",
            (
                "type=glob,source="
                f"{get_test_file_path('test_dirname/foo') + '/*.ext'},"
                "destination=/mnt"
            ),
        ]
        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                *expected_additional_args,
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    @parameterized.expand([
        (
            "absolute_path",
            get_test_file_path('test_dirname/foo'),
            [
                "--mount",
                f"type=bind,source={get_test_file_path('test_dirname/foo')},destination=/mnt",
            ],
        ),
        (
            "relative_path",
            './foo',
            [
                "--mount",
                f"type=bind,source={get_test_file_path('test_dirname/foo')},destination=/mnt",
            ],
        ),
        (
            "home_dir",
            '~/test_dirname/foo',
            [
                "--mount",
                f"type=bind,source={os.path.expanduser('~/test_dirname/foo')},destination=/mnt",
            ],
        ),
    ])
    async def test_volumes_bind_mount_source(
        self, test_name: str, mount_source: str, expected_additional_args: list
    ) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()

        # This is supposed to happen during `_parse_compose_file`
        # but that is probably getting skipped during testing
        cnt["_service"] = cnt["service_name"]

        cnt["volumes"] = [
            {
                "type": "bind",
                "source": f"{mount_source}",
                "target": "/mnt",
            }
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                *expected_additional_args,
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    @parameterized.expand([
        (
            "without_subpath",
            {},
            "type=image,source=example:latest,destination=/mnt/example",
        ),
        (
            "with_subpath",
            {"image": {"subpath": "path/to/image/folder"}},
            "type=image,source=example:latest,destination=/mnt/example,subpath=path/to/image/folder",
        ),
    ])
    async def test_volumes_image_mount(
        self, test_name: str, image_opts: dict, expected_mount_arg: str
    ) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["_service"] = cnt["service_name"]

        cnt["volumes"] = [
            {
                "type": "image",
                "source": "example:latest",
                "target": "/mnt/example",
                **image_opts,
            },
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--mount",
                expected_mount_arg,
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    @parameterized.expand([
        (
            "without_subpath",
            {},
            "type=volume,source=volname,destination=/mnt/example",
        ),
        (
            "with_subpath",
            {"volume": {"subpath": "path/to/image/folder"}},
            "type=volume,source=volname,destination=/mnt/example,subpath=path/to/image/folder",
        ),
    ])
    async def test_volumes_mount(
        self, test_name: str, volume_opts: dict, expected_mount_arg: str
    ) -> None:
        c = create_compose_mock()
        c.vols = {"volname": {"name": "volname"}}

        cnt = get_minimal_container()
        cnt["_service"] = cnt["service_name"]

        cnt["volumes"] = [
            {
                "type": "volume",
                "source": "volname",
                "target": "/mnt/example",
                **volume_opts,
            },
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--mount",
                expected_mount_arg,
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    @parameterized.expand([
        (
            "create_host_path_set_to_true",
            {"bind": {"create_host_path": True}},
        ),
        (
            "create_host_path_default_true",
            {},
        ),
    ])
    async def test_volumes_bind_mount_create_source_dir(self, test_name: str, bind: dict) -> None:
        # creates a missing source dir
        c = create_compose_mock()
        c.prefer_volume_over_mount = True
        cnt = get_minimal_container()

        cnt["_service"] = cnt["service_name"]

        volume_info = {
            "type": "bind",
            "source": "./not_exists/foo",
            "target": "/mnt",
        }
        volume_info.update(bind)
        cnt["volumes"] = [
            volume_info,
        ]

        args = await container_to_args(c, cnt)

        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "-v",
                f"{get_test_file_path('./test_dirname/not_exists/foo')}:/mnt",
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )
        dir_path = get_test_file_path('./test_dirname/not_exists/foo')
        shutil.rmtree(dir_path)

    # throws an error as the source path does not exist and its creation was suppressed with the
    # create_host_path = False option
    async def test_volumes_bind_mount_source_does_not_exist(self) -> None:
        c = create_compose_mock()
        c.prefer_volume_over_mount = True
        cnt = get_minimal_container()

        cnt["_service"] = cnt["service_name"]

        cnt["volumes"] = [
            {
                "type": "bind",
                "source": "./not_exists/foo",
                "target": "/mnt",
                "bind": {"create_host_path": False},
            }
        ]

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    @parameterized.expand([
        ("not_compat", False, "test_project_name", "test_project_name_network1"),
        ("compat_no_dash", True, "test_project_name", "test_project_name_network1"),
        ("compat_dash", True, "test_project-name", "test_projectname_network1"),
    ])
    async def test_network_default_name(
        self, name: str, is_compat: bool, project_name: str, expected_network_name: str
    ) -> None:
        c = create_compose_mock(project_name)
        c.x_podman = {PodmanCompose.XPodmanSettingKey.DEFAULT_NET_NAME_COMPAT: is_compat}
        c.networks = {'network1': {}}

        cnt = get_minimal_container()
        cnt['networks'] = ['network1']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                f"--network={expected_network_name}:alias=service_name",
                "busybox",
            ],
        )

    async def test_device(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()

        cnt['devices'] = ['/dev/ttyS0']
        cnt['device_cgroup_rules'] = ['c 100:200 rwm']

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--device",
                "/dev/ttyS0",
                "--device-cgroup-rule",
                "c 100:200 rwm",
                "--network=bridge:alias=service_name",
                "busybox",
            ],
        )

    async def test_cpuset(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["cpuset"] = "0-1"

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--cpuset-cpus",
                "0-1",
                "busybox",
            ],
        )

    async def test_pids_limit_container_level(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["pids_limit"] = 100

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--pids-limit",
                "100",
                "busybox",
            ],
        )

    async def test_pids_limit_deploy_section(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["deploy"] = {"resources": {"limits": {"pids": 100}}}

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--pids-limit",
                "100",
                "busybox",
            ],
        )

    async def test_pids_limit_both_same(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["pids_limit"] = 100
        cnt["deploy"] = {"resources": {"limits": {"pids": 100}}}

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--pids-limit",
                "100",
                "busybox",
            ],
        )

    async def test_pids_limit_both_different(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["pids_limit"] = 100
        cnt["deploy"] = {"resources": {"limits": {"pids": 200}}}

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)

    async def test_healthcheck_string(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["healthcheck"] = {
            "test": "cmd arg1 arg2",
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--healthcheck-command",
                '["CMD-SHELL", "cmd arg1 arg2"]',
                "busybox",
            ],
        )

    async def test_healthcheck_cmd_args(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["healthcheck"] = {
            "test": ["CMD", "cmd", "arg1", "arg2"],
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--healthcheck-command",
                '["cmd", "arg1", "arg2"]',
                "busybox",
            ],
        )

    async def test_healthcheck_cmd_shell(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["healthcheck"] = {
            "test": ["CMD-SHELL", "cmd arg1 arg2"],
        }

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge:alias=service_name",
                "--healthcheck-command",
                '["cmd arg1 arg2"]',
                "busybox",
            ],
        )

    async def test_healthcheck_cmd_shell_error(self) -> None:
        c = create_compose_mock()
        cnt = get_minimal_container()
        cnt["healthcheck"] = {
            "test": ["CMD-SHELL", "cmd arg1", "arg2"],
        }

        with self.assertRaises(ValueError):
            await container_to_args(c, cnt)
