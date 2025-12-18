import unittest

from parameterized import parameterized

from podman_compose import PodmanCompose
from podman_compose import get_net_args
from tests.unit.test_container_to_args import create_compose_mock

PROJECT_NAME = "test_project_name"
SERVICE_NAME = "service_name"
CONTAINER_NAME = f"{PROJECT_NAME}_{SERVICE_NAME}_1"


def get_networked_compose(num_networks: int = 1) -> PodmanCompose:
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

    if num_networks == 1:
        compose.default_net = "net0"

    return compose


def get_minimal_container() -> dict:
    return {
        "name": CONTAINER_NAME,
        "service_name": SERVICE_NAME,
        "image": "busybox",
    }


class TestGetNetArgs(unittest.TestCase):
    def test_minimal(self) -> None:
        compose = get_networked_compose()
        container = get_minimal_container()

        expected_args = [
            f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_default_net_is_None(self) -> None:
        compose = get_networked_compose()
        container = get_minimal_container()

        mac_address = "11:22:33:44:55:66"
        container["mac_address"] = mac_address

        compose.default_net = None

        expected_args = [
            f"--network=bridge:alias={SERVICE_NAME},mac={mac_address}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_net(self) -> None:
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_alias(self) -> None:
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {}}
        container["_aliases"] = ["alias1", "alias2"]

        expected_args = [
            f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME},alias=alias1,alias=alias2",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_aliases_on_network_scope(self) -> None:
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {"aliases": ["alias1"]}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME},alias=alias1",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_ipv4(self) -> None:
        ip = "192.168.0.42"
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv4_address": ip}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:ip={ip},alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertEqual(expected_args, args)

    def test_one_ipv6(self) -> None:
        ipv6_address = "fd00:0::42"
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv6_address": ipv6_address}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:ip6={ipv6_address},alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_mac(self) -> None:
        mac = "00:11:22:33:44:55"
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {}}
        container["mac_address"] = mac

        expected_args = [
            f"--network={PROJECT_NAME}_net0:mac={mac},alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_one_mac_two_nets(self) -> None:
        mac = "00:11:22:33:44:55"
        compose = get_networked_compose(num_networks=6)
        container = get_minimal_container()
        container["networks"] = {"net0": {}, "net1": {}}
        container["mac_address"] = mac

        expected_args = [
            f"--network={PROJECT_NAME}_net0:mac={mac},alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net1:alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    @parameterized.expand([
        "mac_address",
        "x-podman.mac_address",
    ])
    def test_mac_on_network(self, mac_attr: str) -> None:
        mac = "00:11:22:33:44:55"
        compose = get_networked_compose()
        container = get_minimal_container()
        container["networks"] = {"net0": {mac_attr: mac}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:mac={mac},alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_nets_as_dict(self) -> None:
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {"net0": {}, "net1": {}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net1:alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_nets_as_list(self) -> None:
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = ["net0", "net1"]

        expected_args = [
            f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net1:alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_ipv4(self) -> None:
        ip0 = "192.168.0.42"
        ip1 = "192.168.1.42"
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv4_address": ip0}, "net1": {"ipv4_address": ip1}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:ip={ip0},alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net1:ip={ip1},alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_two_ipv6(self) -> None:
        ip0 = "fd00:0::42"
        ip1 = "fd00:1::42"
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {"net0": {"ipv6_address": ip0}, "net1": {"ipv6_address": ip1}}

        expected_args = [
            f"--network={PROJECT_NAME}_net0:ip6={ip0},alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net1:ip6={ip1},alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    # custom extension; not supported by docker-compose
    def test_two_mac(self) -> None:
        mac0 = "00:00:00:00:00:01"
        mac1 = "00:00:00:00:00:02"
        compose = get_networked_compose(num_networks=2)
        container = get_minimal_container()
        container["networks"] = {
            "net0": {"x-podman.mac_address": mac0},
            "net1": {"x-podman.mac_address": mac1},
        }

        expected_args = [
            f"--network={PROJECT_NAME}_net0:mac={mac0},alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net1:mac={mac1},alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_mixed_mac(self) -> None:
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
            r"specifying mac_address on both container and network level is not supported"
        )
        self.assertRaisesRegex(RuntimeError, expected_exception, get_net_args, compose, container)

    def test_mixed_config(self) -> None:
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
            f"--network={PROJECT_NAME}_net0:ip={ip4_0},ip6={ip6_0},mac={mac},alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net1:ip={ip4_1},alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net2:ip6={ip6_2},alias={SERVICE_NAME}",
            f"--network={PROJECT_NAME}_net3:alias={SERVICE_NAME}",
        ]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    @parameterized.expand([
        ("bridge", [f"--network=bridge:alias={SERVICE_NAME},mac=11:22:33:44:55:66"]),
        (
            "bridge:ip=10.88.0.3",
            [f"--network=bridge:ip=10.88.0.3,alias={SERVICE_NAME},mac=11:22:33:44:55:66"],
        ),
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
    def test_network_modes(self, network_mode: str, expected_args: list) -> None:
        compose = get_networked_compose()
        container = get_minimal_container()
        container["network_mode"] = network_mode

        mac_address = "11:22:33:44:55:66"
        container["network_mode"] = network_mode
        container["mac_address"] = mac_address

        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_network_mode_invalid(self) -> None:
        compose = get_networked_compose()
        container = get_minimal_container()
        container["network_mode"] = "invalid_mode"

        with self.assertRaises(SystemExit):
            get_net_args(compose, container)

    def test_network__mode_service(self) -> None:
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

    def test_pod_network_inheritance_enabled(self) -> None:
        """
        Test that when pod_network is configured and container is in a pod,
        get_net_args returns empty list to allow pod network inheritance.
        """
        from podman_compose import PodmanCompose

        compose = get_networked_compose()
        # Set up pod_network via x_podman
        compose.x_podman = {PodmanCompose.XPodmanSettingKey.POD_NETWORK: "external_macvlan"}
        # Mock the methods that use x_podman
        compose.resolve_pod_network = lambda: "external_macvlan"
        compose.should_inherit_net_from_pod = lambda cnt: (
            compose.resolve_pod_network() is not None
            and cnt.get("pod")
            and not cnt.get("network_mode")
            and not cnt.get("networks")
        )

        container = get_minimal_container()
        container["pod"] = "pod_test_project_name"

        expected_args: list = []
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_pod_network_inheritance_disabled_no_pod(self) -> None:
        """
        Test that when pod_network is configured but container is not in a pod,
        get_net_args returns normal network args.
        """
        from podman_compose import PodmanCompose

        compose = get_networked_compose()
        compose.x_podman = {PodmanCompose.XPodmanSettingKey.POD_NETWORK: "external_macvlan"}
        compose.resolve_pod_network = lambda: "external_macvlan"
        compose.should_inherit_net_from_pod = lambda cnt: (
            compose.resolve_pod_network() is not None
            and cnt.get("pod")
            and not cnt.get("network_mode")
            and not cnt.get("networks")
        )

        container = get_minimal_container()
        # No pod assigned

        expected_args = [f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME}"]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_pod_network_inheritance_disabled_explicit_networks(self) -> None:
        """
        Test that when container has explicit networks config,
        pod network inheritance is skipped even if pod_network is set.
        """
        from podman_compose import PodmanCompose

        compose = get_networked_compose()
        compose.x_podman = {PodmanCompose.XPodmanSettingKey.POD_NETWORK: "external_macvlan"}
        compose.resolve_pod_network = lambda: "external_macvlan"
        compose.should_inherit_net_from_pod = lambda cnt: (
            compose.resolve_pod_network() is not None
            and cnt.get("pod")
            and not cnt.get("network_mode")
            and not cnt.get("networks")
        )

        container = get_minimal_container()
        container["pod"] = "pod_test_project_name"
        container["networks"] = {"net0": {}}  # Explicit networks config

        expected_args = [f"--network={PROJECT_NAME}_net0:alias={SERVICE_NAME}"]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)

    def test_pod_network_inheritance_disabled_network_mode(self) -> None:
        """
        Test that when container has explicit network_mode,
        pod network inheritance is skipped even if pod_network is set.
        """
        from podman_compose import PodmanCompose

        compose = get_networked_compose()
        compose.x_podman = {PodmanCompose.XPodmanSettingKey.POD_NETWORK: "external_macvlan"}
        compose.resolve_pod_network = lambda: "external_macvlan"
        compose.should_inherit_net_from_pod = lambda cnt: (
            compose.resolve_pod_network() is not None
            and cnt.get("pod")
            and not cnt.get("network_mode")
            and not cnt.get("networks")
        )

        container = get_minimal_container()
        container["pod"] = "pod_test_project_name"
        container["network_mode"] = "host"  # Explicit network_mode

        expected_args = ["--network=host"]
        args = get_net_args(compose, container)
        self.assertListEqual(expected_args, args)
