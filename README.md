# PodMan-Compose

A script to run `docker-compose.yml` using [podman](https://podman.io/),
doing necessary mapping to make it work rootless.

## NOTE

it's still underdevelopment and does not work yet.

## Mappings

* `1podfw` - create all containers in one pod (inter-container communication is done via `localhost`), doing port mapping in that pod
* `1pod` - create all containers in one pod, doing port mapping in each container
* `identity` - no mapping
* `hostnet` - use host network, and inter-container communication is done via host gateway and published ports
* `cntnet` - create a container and use it via `--network container:name` (inter-container communication via `localhost`)
* `publishall` - publish all ports to host (using `-P`) and communicate via gateway

## Examples

```
./podman-compose.py -t cntnet -f examples/awx/docker-compose.yml up
```
