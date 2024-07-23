# Podman specific extensions to the docker-compose format

Podman-compose supports the following extension to the docker-compose format. These extensions
are generally specified under fields with "x-podman" prefix in the compose file.

## Container management

The following extension keys are available under container configuration:

* `x-podman.uidmaps` - Run the container in a new user namespace using the supplied UID mapping.

* `x-podman.gidmaps` - Run the container in a new user namespace using the supplied GID mapping.

* `x-podman.rootfs` - Run the container without requiring any image management; the rootfs of the
container is assumed to be managed externally.

For example, the following docker-compose.yml allows running a podman container with externally managed rootfs.
```yml
version: "3"
services:
    my_service:
        command: ["/bin/busybox"]
        x-podman.rootfs: "/path/to/rootfs"
```

For explanations of these extensions, please refer to the [Podman Documentation](https://docs.podman.io/).


## Per-network MAC-addresses

Generic docker-compose files support specification of the MAC address on the container level. If the
container has multiple network interfaces, the specified MAC address is applied to the first
specified network.

Podman-compose in addition supports the specification of MAC addresses on a per-network basis. This
is done by adding a `x-podman.mac_address` key to the network configuration in the container. The
value of the `x-podman.mac_address` key is the MAC address to be used for the network interface.

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
        x-podman.mac_address: "02:bb:bb:bb:bb:bb"
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
