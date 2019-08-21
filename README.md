# podman-compose

A script to run `docker-compose.yml` using [podman](https://podman.io/),
doing necessary mapping to make it work rootless.

    Note, that it's still under development and might not work well yet.

## Installation

Install latest stable version from PyPI:

```
pip install podman-compose
```

Or latest stable version from GitHub:

```
pip install https://github.com/muayyad-alsadi/podman-compose/archive/master.tar.gz
```

Or latest development version from GitHub:

```
pip install https://github.com/muayyad-alsadi/podman-compose/archive/devel.tar.gz
```

## Mappings

* `1podfw` - create all containers in one pod (inter-container communication is done via `localhost`), doing port mapping in that pod.
* `1pod` - create all containers in one pod, doing port mapping in each container.
* `identity` - no mapping.
* `hostnet` - use host network, and inter-container communication is done via host gateway and published ports.
* `cntnet` - create a container and use it via `--network container:name` (inter-container communication via `localhost`).
* `publishall` - publish all ports to host (using `-P`) and communicate via gateway.

## Examples

When testing the `AWX`, if you got errors just wait for db migrations to end. 

### Working Example

*Tested on latest ``podman`` (commit `349e69..` on 2019-03-11).*

By using many containers on a single pod that shares the network (services talk 
via localhost):

```
./podman-compose.py -t 1podfw -f examples/awx3/docker-compose.yml up
```

Or by reusing a container network and `--add-host`:

```
$ ./podman-compose.py -t cntnet -f examples/awx3/docker-compose.yml up
```

Or by using host network and localhost works as follows:

```
$ ./podman-compose.py -t hostnet -f examples/awx3-hostnet-localhost/docker-compose.yml up
```

### Work in progress

```
./podman-compose.py -t 1pod -f examples/awx3/docker-compose.yml up
```
