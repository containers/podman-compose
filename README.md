# Podman Compose

An implementation of `docker-compose` with [podman](https://podman.io/) backend.
The main objective of this project is to be able to run `docker-compose.yml` unmodified and rootless.
This project is aimed to provide drop-in replacement for `docker-compose`,
and it's very useful for certain cases because:

- can run rootless
- only depend on `podman` and Python3 and [PyYAML](https://pyyaml.org/)
- no daemon, no setup.
- can be used by developers to run single-machine containerized stacks using single familiar YAML file

For production-like single-machine containerized environment consider

- [k3s](https://k3s.io) | [k3s github](https://github.com/rancher/k3s)
- [MiniKube](https://minikube.sigs.k8s.io/)
- [MiniShift](https://www.okd.io/minishift/)


For the real thing (multi-node clusters) check any production
OpenShift/Kubernetes distribution like [OKD](https://www.okd.io/minishift/).

## NOTE

This project is still underdevelopment.

## Installation

Install latest stable version from PyPI:

```
pip3 install podman-compose
```

pass `--user` to install inside regular user home without being root.

Or latest development version from GitHub:

```
pip3 install https://github.com/containers/podman-compose/archive/devel.tar.gz
```

or

```
curl -o /usr/local/bin/podman-compose https://raw.githubusercontent.com/containers/podman-compose/devel/podman_compose.py
chmod +x /usr/local/bin/podman-compose
```

or 

```
curl -o ~/.local/bin/podman-compose https://raw.githubusercontent.com/containers/podman-compose/devel/podman_compose.py
chmod +x ~/.local/bin/podman-compose
```

or install from Fedora (starting from f31) repositories:

```
sudo dnf install podman-compose
```

## Basic Usage

We have included fully functional sample stacks inside `examples/` directory.

A quick example would be

```
cd examples/busybox
podman-compose --help
podman-compose up --help
podman-compose up
```

A more rich example can be found in [examples/awx3](examples/awx3)
which have

- A Postgres Database
- RabbitMQ server
- MemCached server
- a django web server
- a django tasks


When testing the `AWX3` example, if you got errors just wait for db migrations to end. 


## Tests

Inside `tests/` directory we have many useless docker-compose stacks
that are meant to test as much cases as we can to make sure we are compatible

## How it works

The default mapping `1podfw` creates a single pod and attach all containers to
its network namespace so that all containers talk via localhost.
For more information see [docs/Mappings.md](docs/Mappings.md).

If you are running as root, you might use identity mapping.

