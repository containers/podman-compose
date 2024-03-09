import unittest

from podman_compose import get_network_create_args


class TestGetNetworkCreateArgs(unittest.TestCase):
    def test_minimal(self):
        net_desc = {
            "labels": [],
            "internal": False,
            "driver": None,
            "driver_opts": {},
            "ipam": {"config": []},
            "enable_ipv6": False,
        }
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)

    def test_ipv6(self):
        net_desc = {
            "labels": [],
            "internal": False,
            "driver": None,
            "driver_opts": {},
            "ipam": {"config": []},
            "enable_ipv6": True,
        }
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--ipv6",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)

    def test_bridge(self):
        net_desc = {
            "labels": [],
            "internal": False,
            "driver": "bridge",
            "driver_opts": {"opt1": "value1", "opt2": "value2"},
            "ipam": {"config": []},
            "enable_ipv6": False,
        }
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--driver",
            "bridge",
            "--opt",
            "opt1=value1",
            "--opt",
            "opt2=value2",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)

    def test_ipam_driver_default(self):
        net_desc = {
            "labels": [],
            "internal": False,
            "driver": None,
            "driver_opts": {},
            "ipam": {
                "driver": "default",
                "config": [
                    {
                        "subnet": "192.168.0.0/24",
                        "ip_range": "192.168.0.2/24",
                        "gateway": "192.168.0.1",
                    }
                ],
            },
        }
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--subnet",
            "192.168.0.0/24",
            "--ip-range",
            "192.168.0.2/24",
            "--gateway",
            "192.168.0.1",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)

    def test_ipam_driver(self):
        net_desc = {
            "labels": [],
            "internal": False,
            "driver": None,
            "driver_opts": {},
            "ipam": {
                "driver": "someipamdriver",
                "config": [
                    {
                        "subnet": "192.168.0.0/24",
                        "ip_range": "192.168.0.2/24",
                        "gateway": "192.168.0.1",
                    }
                ],
            },
        }
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--ipam-driver",
            "someipamdriver",
            "--subnet",
            "192.168.0.0/24",
            "--ip-range",
            "192.168.0.2/24",
            "--gateway",
            "192.168.0.1",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)

    def test_complete(self):
        net_desc = {
            "labels": ["label1", "label2"],
            "internal": True,
            "driver": "bridge",
            "driver_opts": {"opt1": "value1", "opt2": "value2"},
            "ipam": {
                "driver": "someipamdriver",
                "config": [
                    {
                        "subnet": "192.168.0.0/24",
                        "ip_range": "192.168.0.2/24",
                        "gateway": "192.168.0.1",
                    }
                ],
            },
            "enable_ipv6": True,
        }
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--label",
            "label1",
            "--label",
            "label2",
            "--internal",
            "--driver",
            "bridge",
            "--opt",
            "opt1=value1",
            "--opt",
            "opt2=value2",
            "--ipam-driver",
            "someipamdriver",
            "--ipv6",
            "--subnet",
            "192.168.0.0/24",
            "--ip-range",
            "192.168.0.2/24",
            "--gateway",
            "192.168.0.1",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)
