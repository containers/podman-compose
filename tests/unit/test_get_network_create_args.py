import unittest
from typing import Any

from podman_compose import get_network_create_args


class TestGetNetworkCreateArgs(unittest.TestCase):
    def get_minimal_net_desc(self) -> dict[str, Any]:
        return {
            "labels": [],
            "internal": False,
            "driver": None,
            "driver_opts": {},
            "ipam": {"config": []},
            "enable_ipv6": False,
        }

    def test_minimal(self) -> None:
        net_desc = self.get_minimal_net_desc()
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

    def test_ipv6(self) -> None:
        net_desc = self.get_minimal_net_desc()
        net_desc["enable_ipv6"] = True
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

    def test_bridge(self) -> None:
        net_desc = self.get_minimal_net_desc()
        net_desc["driver"] = "bridge"
        net_desc["driver_opts"] = {"opt1": "value1", "opt2": "value2"}
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

    def test_ipam_driver_default(self) -> None:
        net_desc = self.get_minimal_net_desc()
        net_desc["ipam"] = {
            "driver": "default",
            "config": [
                {
                    "subnet": "192.168.0.0/24",
                    "ip_range": "192.168.0.2/24",
                    "gateway": "192.168.0.1",
                }
            ],
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

    def test_ipam_driver(self) -> None:
        net_desc = self.get_minimal_net_desc()
        net_desc["ipam"] = {
            "driver": "someipamdriver",
            "config": [
                {
                    "subnet": "192.168.0.0/24",
                    "ip_range": "192.168.0.2/24",
                    "gateway": "192.168.0.1",
                }
            ],
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

    def test_complete(self) -> None:
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

    def test_disable_dns(self) -> None:
        net_desc = self.get_minimal_net_desc()
        net_desc["x-podman.disable_dns"] = True
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--disable-dns",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)

    def test_dns_string(self) -> None:
        net_desc = self.get_minimal_net_desc()
        net_desc["x-podman.dns"] = "192.168.1.2"
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--dns",
            "192.168.1.2",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)

    def test_dns_list(self) -> None:
        net_desc = self.get_minimal_net_desc()
        net_desc["x-podman.dns"] = ["192.168.1.2", "192.168.1.3"]
        proj_name = "test_project"
        net_name = "test_network"
        expected_args = [
            "create",
            "--label",
            f"io.podman.compose.project={proj_name}",
            "--label",
            f"com.docker.compose.project={proj_name}",
            "--dns",
            "192.168.1.2,192.168.1.3",
            net_name,
        ]
        args = get_network_create_args(net_desc, proj_name, net_name)
        self.assertEqual(args, expected_args)
