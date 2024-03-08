# Podman Compose
## [![Tests](https://github.com/containers/podman-compose/actions/workflows/test.yml/badge.svg)](https://github.com/containers/podman-compose/actions/workflows/test.yml)

An implementation of [Compose Spec](https://compose-spec.io/) with [Podman](https://podman.io/) backend.
This project focuses on:

* rootless
* daemon-less process model, we directly execute podman, no running daemon.

This project only depends on:

* `podman`
* [podman dnsname plugin](https://github.com/containers/dnsname): It is usually found in the `podman-plugins` or `podman-dnsname` distro packages, those packages are not pulled by default and you need to install them. This allows containers to be able to resolve each other if they are on the same CNI network.
* Python3
* [PyYAML](https://pyyaml.org/)
* [python-dotenv](https://pypi.org/project/python-dotenv/)

And it's formed as a single Python file script that you can drop into your PATH and run.

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

Modern podman versions (>=3.4) do not have those limitations, and thus you can use latest and stable 1.x branch.

If you are upgrading from `podman-compose` version `0.1.x` then we no longer have global option `-t` to set mapping type
like `hostnet`. If you desire that behavior, pass it the standard way like `network_mode: host` in the YAML.


## Installation

Install the latest stable version from PyPI:

```
pip3 install podman-compose
```

pass `--user` to install inside regular user home without being root.

Or latest development version from GitHub:

```
pip3 install https://github.com/containers/podman-compose/archive/devel.tar.gz
```


or install from Fedora (starting from f31) repositories:

```
sudo dnf install podman-compose
```

## Basic Usage

We have included fully functional sample stacks inside `examples/` directory.
You can get more examples from [awesome-compose](https://github.com/docker/awesome-compose).


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


When testing the `AWX3` example, if you got errors, just wait for db migrations to end.
There is also AWX 17.1.0

## Tests

Inside `tests/` directory we have many useless docker-compose stacks
that are meant to test as many cases as we can to make sure we are compatible

### Unit tests with unittest
run a unittest with following command

```shell
python -m unittest pytests/*.py
```

# Contributing guide

If you are a user or a developer and want to contribute please check the [CONTRIBUTING](CONTRIBUTING.md) section
