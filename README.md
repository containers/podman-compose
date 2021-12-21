# Podman Compose

An implementation of [Compose Spec](https://compose-spec.io/) with [Podman](https://podman.io/) backend.
This project focus on:

* rootless
* daemon-less process model, we directly execute podman, no running daemon.

This project only depend on:

* `podman`
* Python3
* [PyYAML](https://pyyaml.org/)
* [python-dotenv](https://pypi.org/project/python-dotenv/)

And it's formed as a single python file script that you can drop into your PATH and run.

## References:

* [spec.md](https://github.com/compose-spec/compose-spec/blob/master/spec.md)
* [docker-compose compose-file-v3](https://docs.docker.com/compose/compose-file/compose-file-v3/)
* [docker-compose compose-file-v2](https://docs.docker.com/compose/compose-file/compose-file-v2/)

## Alternatives

As in [this article](https://fedoramagazine.org/use-docker-compose-with-podman-to-orchestrate-containers-on-fedora/) you can setup a `podman.socket` and use unmodified `docker-compose` that talks to that socket but in this case you lose the process-model (ex. `docker-compose build` will send a possibly large context tarball to the daemon)

For production-like single-machine containerized environment consider

- [k3s](https://k3s.io) | [k3s github](https://github.com/rancher/k3s)
- [MiniKube](https://minikube.sigs.k8s.io/)

For the real thing (multi-node clusters) check any production
OpenShift/Kubernetes distribution like [OKD](https://www.okd.io/).

## Versions

If you have legacy version of `podman` (before 3.1.0) you might need to stick with legacy `podman-compose` `0.1.x` branch.
The legacy branch 0.1.x uses mappings and workarounds to compensate for rootless limitations.

Modern podman versions (>=3.4) do not have those limitations and thus you can use latest and stable 1.x branch.

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

or inside your home

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
There is also AWX 17.1.0

## Tests

Inside `tests/` directory we have many useless docker-compose stacks
that are meant to test as much cases as we can to make sure we are compatible


