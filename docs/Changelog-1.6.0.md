Version 1.6.0 (2026-06-03)
==========================

Bug fixes
---------

- Implemented volumes bind `create_host_path` option.
- Implemented colored, service-name-only default for `logs` command.
- Added `--no-color` flag for `podman-compose logs` command.
- Cleaned up error messages when external network or volume is missing, including a suggested `podman network create` / `podman volume create` command.
- Fixed crash on parsing empty top-level objects in compose file
- Images that have names starting with `localhost/` will no longer be
  pulled when both image and build sections exist.
- Fixed link resolution for mounted volume when volume source is a symlink.
- Fixed `podman-compose down service` stops wrong dependents
- Fixed the bug in parsing to add identify `extra-hosts` field in build parameters.
- Fixed TypeError when parsing 'include' items that are formatted as detailed mappings (dictionaries).
- Fixed shell error: `unknown flag: --policy`.
- Fixed !reset and !override tags used used with extended compose file
- Fixed freeze caused by too long log lines containing multibyte characters.
- Fixed crash on merging named volumes with driver options into the uncustomized named volumes
- Fixed `--pull` option in `build` and `up` command can not set to pull policy explicitly.
- Implemented returning error code from `pull` command.
- The `target` suboption on mount-type external secrets is now honored.
- Added support for service level configuration change detection on up command
- Fixed top-level `name` attribute interpolation not happening.


Changes
-------

- Better error message when probing for podman fails.
- Renamed healthcheck flags to be consistent with Podman options.

Features
--------

- Implemented --wait and --wait-timeout for podman-compose up and start.
- Added support for 'glob' mount type when defining volumes.
- Added support for COMPOSE_PROFILES environment variable to enable profiles.
- Added support for volume.type=image in services, for mounting files from container images.
- Added support for nested variable interpolation
- Images are now pull before container teardown on compose up, which reduce the downtime of services.
- Added support for `environment` as a secret source for build secrets.
- Added support for `service:service_name` contexts in `build.additional_contexts`.
- Add support for `start_interval` option.
