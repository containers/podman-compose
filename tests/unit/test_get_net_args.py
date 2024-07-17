import unittest

from parameterized import parameterized

from podman_compose import get_net_args
from tests.unit.test_container_to_args import create_compose_mock

PROJECT_NAME = "test_project_name"
SERVICE_NAME = "service_name"
CONTAINER_NAME = f"{PROJECT_NAME}_{SERVICE_NAME}_1"


def get_networked_compose(num_networks=1):
    compose = create_compose_mock(PROJECT_NAME)
    for network in range(num_networks):
        compose.networks[f"net{network}"] = {
            "driver": "bridge",
            "ipam": {
                "config": [
                    {"subnet": f"192.168.{network}.0/24"},
                    {"subnet": f"fd00:{network}::/64"},
                ]
            },
            "enable_ipv6": True,
        }

    return compose


def get_minimal_container():
    return {
        "name": CONTAINER_NAME,
        "service_name": SERVICE_NAME,
        "image": "busybox",
    }


class TestGetNetArgs(unittest.TestCase):
    def test_minimal(self):
        compose = get_networked_compose()
        container = get_minimal_container()

        expected_args = [
            "--network=bridge",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_net(self):
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_alias(self):
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {}}
        container["_aliases"] = ["alias1", "alias2"]

        expected_args = [
            f"--network={PROJECT_NAME}_net0",
            f"--network-alias={SERVICE_NAME}",
            "--network-alias=alias1",
            "--network-alias=alias2",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_ipv4(self):
        ip = "192.168.0.42"
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv4_address": ip}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0",
            f"--ip={ip}",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertEqual(expected_args, args)

    def test_one_ipv6(self):
        ipv6_address = "fd00:0::42"
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv6_address": ipv6_address}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0",
            f"--ip6={ipv6_address}",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_mac(self):
        mac = "00:11:22:33:44:55"
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {}}
        container["mac_address"] = mac

        expected_args = [
            f"--network={PROJECT_NAME}_net0",
            f"--mac-address={mac}",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_mac_two_nets(self):
        mac = "00:11:22:33:44:55"
        compose = get_networked_compose(num_networks=6)
        container = get_minimal_container()
        container["networks"] = {"net0": {}, "net1": {}}
        container["mac_address"] = mac

        expected_args = [
            f"--network={PROJECT_NAME}_net0:mac={mac}",
            f"--network={PROJECT_NAME}_net1",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_nets_as_dict(self):
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {"net0": {}, "net1": {}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0",
            f"--network={PROJECT_NAME}_net1",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_nets_as_list(self):
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = ["net0", "net1"]

        expected_args = [
            f"--network={PROJECT_NAME}_net0",
            f"--network={PROJECT_NAME}_net1",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_ipv4(self):
        ip0 = "192.168.0.42"
        ip1 = "192.168.1.42"
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv4_address": ip0}, "net1": {"ipv4_address": ip1}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:ip={ip0}",
            f"--network={PROJECT_NAME}_net1:ip={ip1}",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_ipv6(self):
        ip0 = "fd00:0::42"
        ip1 = "fd00:1::42"
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv6_address": ip0}, "net1": {"ipv6_address": ip1}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:ip={ip0}",
            f"--network={PROJECT_NAME}_net1:ip={ip1}",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    # custom extension; not supported by docker-compose
    def test_two_mac(self):
        mac0 = "00:00:00:00:00:01"
        mac1 = "00:00:00:00:00:02"
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {
            "net0": {"x-podman.mac_address": mac0},
            "net1": {"x-podman.mac_address": mac1},
        }

        expected_args = [
            f"--network={PROJECT_NAME}_net0:mac={mac0}",
            f"--network={PROJECT_NAME}_net1:mac={mac1}",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_mixed_mac(self):
        ip4_0 = "192.168.0.42"
        ip4_1 = "192.168.1.42"
        ip4_2 = "192.168.2.42"
        mac_0 = "00:00:00:00:00:01"
        mac_1 = "00:00:00:00:00:02"

        compose = get_networked_compose(num_networks=3)
        container = get_minimal_container()
        container["networks"] = {
            "net0": {"ipv4_address": ip4_0},
            "net1": {"ipv4_address": ip4_1, "x-podman.mac_address": mac_0},
            "net2": {"ipv4_address": ip4_2},
        }
        container["mac_address"] = mac_1

        expected_exception = (
            r"specifying mac_address on both container and network level " r"is not supported"
        )
        self.assertRaisesRegex(RuntimeError, expected_exception, get_net_args, compose, container)

    def test_mixed_config(self):
        ip4_0 = "192.168.0.42"
        ip4_1 = "192.168.1.42"
        ip6_0 = "fd00:0::42"
        ip6_2 = "fd00:2::42"
        mac = "00:11:22:33:44:55"
        compose = get_networked_compose(num_networks=4)
        container = get_minimal_container()
        container["networks"] = {
            "net0": {"ipv4_address": ip4_0, "ipv6_address": ip6_0},
            "net1": {"ipv4_address": ip4_1},
            "net2": {"ipv6_address": ip6_2},
            "net3": {},
        }
        container["mac_address"] = mac

        expected_args = [
            f"--network={PROJECT_NAME}_net0:ip={ip4_0},ip={ip6_0},mac={mac}",
            f"--network={PROJECT_NAME}_net1:ip={ip4_1}",
            f"--network={PROJECT_NAME}_net2:ip={ip6_2}",
            f"--network={PROJECT_NAME}_net3",
            f"--network-alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    @parameterized.expand([
        ("bridge", ["--network=bridge", f"--network-alias={SERVICE_NAME}"]),
        ("host", ["--network=host"]),
        ("none", ["--network=none"]),
        ("slirp4netns", ["--network=slirp4netns"]),
        ("slirp4netns:cidr=10.42.0.0/24", ["--network=slirp4netns:cidr=10.42.0.0/24"]),
        ("private", ["--network=private"]),
        ("pasta", ["--network=pasta"]),
        ("pasta:--ipv4-only,-a,10.0.2.0", ["--network=pasta:--ipv4-only,-a,10.0.2.0"]),
        ("ns:my_namespace", ["--network=ns:my_namespace"]),
        ("container:my_container", ["--network=container:my_container"]),
    ])
    def test_network_modes(self, network_mode, expected_args):
        compose = get_networked_compose()
        container = get_minimal_container()
        container["network_mode"] = network_mode

        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_network_mode_invalid(self):
        compose = get_networked_compose()
        container = get_minimal_container()
        container["network_mode"] = "invalid_mode"

        with self.assertRaises(SystemExit):
            get_net_args(compose, container)

    def test_network__mode_service(self):
        compose = get_networked_compose()
        compose.container_names_by_service = {
            "service_1": ["container_1"],
            "service_2": ["container_2"],
        }

        container = get_minimal_container()
        container["network_mode"] = "service:service_2"

        expected_args = ["--network=container:container_2"]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)
