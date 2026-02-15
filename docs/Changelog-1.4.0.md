Version 1.4.0 (2025-05-10)
==========================

Bug fixes
---------

- Fixed handling of relative includes and extends in compose files
- Fixed error when merging arguments in list and dictionary syntax
- Fixed issue where short-lived containers could execute twice when using `up` in detached mode
- Fixed `up` command hanging on Podman versions earlier than 4.6.0
- Fixed issue where `service_healthy` conditions weren't enforced during `up` command
- Fixed support for the `--scale` flag
- Fixed bug causing dependent containers to start despite `--no-deps` flag
- Fixed port command behavior for dynamic host ports
- Fixed interpolation of `COMPOSE_PROJECT_NAME` when set from top-level `name` in compose file
- Fixed project name evaluation order to match compose spec
- Fixed build context when using git URLs
- Fixed `KeyError` when `down` is called with non-existent service
- Skip `down` during `up` when no active containers exist
- Fixed non-zero exit code on failure when using `up -d`
- Fixed SIGINT handling during `up` command for graceful shutdown
- Fixed `NotImplementedError` when interrupted on Windows

Features
--------

- Added `--quiet` flag to `config` command to suppress output
- Added support for `pids_limit` and `deploy.resources.limits.pids`
- Added `--abort-on-container-failure` option
- Added `--rmi` argument to `down` command for image removal
- Added support for `x-podman.disable-dns` to disable DNS plugin on defined networks
- Added support for `x-podman.dns` to set DNS nameservers for defined networks
- Improved file descriptor handling by no longer closing externally created descriptors.
  This allows descriptors created e.g. via systemd socket activation to be passed to
  containers.
- Added support for `cpuset` configuration
- Added support for `reset` and `override` tags when merging compose files
- Added support for `x-podman.interface_name` to set network interface names
- Added support for `x-podman.pod_args` to override default `--pod-args`
