Version 1.5.0 (2025-07-07)
==========================

Bug fixes
---------

- Fixed path to a local SSH key to be relative to the directory of compose file during build.
- Fixed CMD healthchecks to run the given command directly and not use `/bin/sh -c`.
- Fixed regression of dockerfile definition if current directory name ends with ".git".
- Fixed exit code from `push` command.
- Implemented short syntax for environment variables set in `.env` for compose.yml `environment:` section.
- Fixed regression of log output including "text" in detached mode.
- Implemented `up --no-recreate` to work as advertised.
- Stack traces emitted due to YAML parse errors are now hidden.


Features
--------

- Added unregister command to remove systemd service registration (`podman-compose systemd -a unregister`)
- Added new `docker_compose_compat` `x-podman` meta setting to enable all Docker Compose compatibility settings
- Added new `name_separator_compat` `x-podman` setting to change name separator to hyphen, same as Docker Compose.
- Added support for environment variable interpolation for YAML keys.
- Added `io.podman.compose.service` label to created containers. It contains the same value as
  `com.docker.compose.service`.
- Added relabel option to secret to make possible to read the secret file by the container process.
- Added support for setting x-podman values using PODMAN_COMPOSE_* environment variables.
- Added support to set `--route` option to `podman network create` via
  `x-podman.routes` key on network configuration.
- Implemented support for custom pod names in `--in-pod`. 
