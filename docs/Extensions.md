# Overview

Podman-compose extends the compose specification to support some unique features of Podman. These extensions can be specified in the compose file under the "x-podman" field.

Currently, podman-compose supports the following extensions:

* `uidmap` - Run the container in a new user namespace using the supplied UID mapping.

* `gidmap` - Run the container in a new user namespace using the supplied GID mapping.

* `rootfs` - Run the container without requiring any image management; the rootfs of the container is assumed to be managed externally.

For example, the following docker-compose.yml allows running a podman container with externally managed rootfs.
```yml
version: "3"
services:
    my_service:
      command: ["/bin/busybox"]
      x-podman:
        rootfs: "/path/to/rootfs"
```

For explanations of these extensions, please refer to the [Podman Documentation](https://docs.podman.io/).
