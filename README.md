# Podman Compose
## [![Tests](https://github.com/containers/podman-compose/actions/workflows/test.yml/badge.svg)](https://github.com/containers/podman-compose/actions/workflows/test.yml)

An implementation of [Compose Spec](https://compose-spec.io/) with [Podman](https://podman.io/) backend.
This project focuses on:

* rootless
* daemon-less process model, we directly execute podman, no running daemon.

This project only depends on:

* `podman`
* [podman dnsname plugin](https://github.com/containers/dnsname): It is usually found in
  the `podman-plugins` or `podman-dnsname` distro packages, those packages are not pulled
  by default and you need to install them. This allows containers to be able to resolve
  each other if they are on the same CNI network. This is not necessary when podman is using
  netavark as a network backend.
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

### Pip

Install the latest stable version from PyPI:

```bash
pip3 install podman-compose
```

pass `--user` to install inside a regular user's home without being root.

Or latest development version from GitHub:

```bash
pip3 install https://github.com/containers/podman-compose/archive/main.tar.gz
```

### Package repositories

podman-compose is available from the following package repositories:

Debian:

```bash
sudo apt install podman-compose
```

Fedora (starting from f31) repositories:

```bash
sudo dnf install podman-compose
```

Homebrew:

```bash
brew install podman-compose
```

### Generate binary using docker/podman locally
This script will download the repo, generate the binary using [this Dockerfile](https://github.com/containers/podman-compose/blob/main/Dockerfile), and place the binary in the directory where you called this script.
```bash
sh -c "$(curl -sSL https://raw.githubusercontent.com/containers/podman-compose/main/scripts/download_and_build_podman-compose.sh)"
```

### Manual

```bash
curl -o /usr/local/bin/podman-compose https://raw.githubusercontent.com/containers/podman-compose/main/podman_compose.py
chmod +x /usr/local/bin/podman-compose
```

or inside your home

```bash
curl -o ~/.local/bin/podman-compose https://raw.githubusercontent.com/containers/podman-compose/main/podman_compose.py
chmod +x ~/.local/bin/podman-compose
```

## Tests

podman-compose is tested via unit and integration tests.

Unit tests can be run via the following:

```shell
python3 -m unittest discover tests/unit
```

Integration tests can be run via the following:

```shell
python3 -m unittest discover tests/integration
```

# Contributing guide

If you are a user or a developer and want to contribute please check the [CONTRIBUTING](CONTRIBUTING.md) section
