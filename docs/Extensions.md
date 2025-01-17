# Podman specific extensions to the docker-compose format

Podman-compose supports the following extension to the docker-compose format. These extensions
are generally specified under fields with "x-podman" prefix in the compose file.

## Container management

The following extension keys are available under container configuration:

* `x-podman.uidmaps` - Run the container in a new user namespace using the supplied UID mapping.

* `x-podman.gidmaps` - Run the container in a new user namespace using the supplied GID mapping.

* `x-podman.rootfs` - Run the container without requiring any image management; the rootfs of the
container is assumed to be managed externally.

* `x-podman.no_hosts` - Run the container without creating /etc/hosts file

For example, the following docker-compose.yml allows running a podman container with externally managed rootfs.
```yml
version: "3"
services:
    my_service:
        command: ["/bin/busybox"]
        x-podman.rootfs: "/path/to/rootfs"
```

For explanations of these extensions, please refer to the [Podman Documentation](https://docs.podman.io/).

## Network management

The following extension keys are available under network configuration:

* `x-podman.disable-dns` - Disable the DNS plugin for the network when set to 'true'.
* `x-podman.dns` - Set nameservers for the network using supplied addresses (cannot be used with x-podman.disable-dns`).

For example, the following docker-compose.yml allows all containers on the same network to use the
specified nameservers:
```yml
version: "3"
network:
  my_network:
    x-podman.dns:
      - "10.1.2.3"
      - "10.1.2.4"
```

For explanations of these extensions, please refer to the
[Podman network create command Documentation](https://docs.podman.io/en/latest/markdown/podman-network-create.1.html).

## Per-network MAC-addresses

Generic docker-compose files support specification of the MAC address on the container level. If the
container has multiple network interfaces, the specified MAC address is applied to the first
specified network.

Podman-compose in addition supports the specification of MAC addresses on a per-network basis. This
is done by adding a `x-podman.mac_address` key to the network configuration in the container. The
value of the `x-podman.mac_address` key is the MAC address to be used for the network interface.

Note that the [compose spec](https://github.com/compose-spec/compose-spec/blob/main/05-services.md#mac_address)
now supports `mac_address` on the network level, so we recommend using
the standard `mac_address` key for setting the MAC address. The
`x-podman.mac_address` is still supported for backwards compatibility.


Specifying a MAC address for the container and for individual networks at the same time is not
supported.

Example:

```yaml
---
version: "3"

networks:
  net0:
    driver: "bridge"
    ipam:
      config:
        - subnet: "192.168.0.0/24"
  net1:
    driver: "bridge"
    ipam:
      config:
        - subnet: "192.168.1.0/24"

services:
  webserver
    image: "busybox"
    command: ["/bin/busybox", "httpd", "-f", "-h", "/etc", "-p", "8001"]
    networks:
      net0:
        ipv4_address: "192.168.0.10"
        x-podman.mac_address: "02:aa:aa:aa:aa:aa"
      net1:
        ipv4_address: "192.168.1.10"
        mac_address: "02:bb:bb:bb:bb:bb" # mac_address is supported
```

## Podman-specific network modes

Generic docker-compose supports the following values for `network-mode` for a container:

- `bridge`
- `host`
- `none`
- `service`
- `container`

In addition, podman-compose supports the following podman-specific values for `network-mode`:

- `slirp4netns[:<options>,...]`
- `ns:<options>`
- `pasta[:<options>,...]`
- `private`

The options to the network modes are passed to the `--network` option of the `podman create` command
as-is.


## Compatibility of default network names between docker-compose and podman-compose

Current versions of podman-compose may produce different default external network names than
docker-compose under certain conditions. Specifically, docker-compose removes dashes (`-` character)
from project name.

To enable compatibility between docker-compose and podman-compose, specify
`default_net_name_compat: true` under global `x-podman` key:

```
x-podman:
    default_net_name_compat: true
```

By default `default_net_name_compat` is `false`. This will change to `true` at some point and the
setting will be removed.

## Compatibility of default network behavior between docker-compose and podman-compose

When there is no network defined (neither network-mode nor networks) in service,
The behavior of default network in docker-compose and podman-compose are different.

| Top-level networks             | podman-compose             | docker-compose |
| ------------------------------ | -------------------------- | -------------- |
| No networks                    | default                    | default        |
| One network named net0         | net0                       | default        |
| Two networks named net0, net1  | podman(`--network=bridge`) | default        |
| Contains network named default | default                    | default        |

To enable compatibility between docker-compose and podman-compose, specify
`default_net_behavior_compat: true` under global `x-podman` key:

```yaml
x-podman:
    default_net_behavior_compat: true
```

## Custom pods management

Podman-compose can have containers in pods. This can be controlled by extension key x-podman in_pod.
It allows providing custom value for --in-pod and is especially relevant when --userns has to be set.

For example, the following docker-compose.yml allows using userns_mode by overriding the default
value of --in-pod (unless it was specifically provided by "--in-pod=True" in command line interface).
```yml
version: "3"
services:
    cont:
        image: nopush/podman-compose-test
        userns_mode: keep-id:uid=1000
        command: ["dumb-init", "/bin/busybox", "httpd", "-f", "-p", "8080"]

x-podman:
    in_pod: false
```
