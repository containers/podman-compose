# Podman specific extensions to the docker-compose format

Podman-compose supports the following extension to the docker-compose format.

## Per-network MAC-addresses

Generic docker-compose files support specification of the MAC address on the container level. If the
container has multiple network interfaces, the specified MAC address is applied to the first
specified network.

Podman-compose in addition supports the specification of MAC addresses on a per-network basis. This
is done by adding a `podman.mac_address` key to the network configuration in the container. The
value of the `podman.mac_address` key is the MAC address to be used for the network interface.

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
        podman.mac_address: "02:aa:aa:aa:aa:aa"
      net1:
        ipv4_address: "192.168.1.10"
        podman.mac_address: "02:bb:bb:bb:bb:bb"
```
