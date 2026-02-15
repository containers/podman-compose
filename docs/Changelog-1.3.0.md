Version 1.3.0 (2025-01-07)
==========================

Bug fixes
---------

- Fixed support for de-facto alternative `Dockerfile` names (e.g. `Containerfile`)
- Fixed a bug that caused attempts to create already existing pods multiple times.
- Fixed compatibility with docker-compose in how symlinks to docker-compose.yml are handled.
- Fixed freeze caused by too long log lines without a newline.
- Fixed support for `network_mode: none`.
- Improved error detection by rejecting service definitions that contain both `network_mode` and
  `networks` keys, which is not allowed.


Features
--------

- Added support for build labels.
- Added support for "platform" property in the build command.
- Added support for "ssh" property in the build command.
- Added support for cache_from and cache_to fields in build section.
- Added support for honoring the condition in the depends_on section of the service, if stated.
- Added `x-podman.no_hosts` setting to pass `--no-hosts` to podman run
- Added support for compatibility with docker compose for default network behavior when no network
  defined in service. This is controlled via `default_net_behavior_compat` feature flag.
- Added a way to get compatibility of default network names with docker compose.
  This is selected by setting `default_net_name_compat: true` on `x-podman` global dictionary.
- Added support for the `device_cgroup_rules` property in services.
- Added support for removing networks in `podman-compose down`.
- Added support for network scoped service aliases.
- Added support for network level `mac_address` attribute.
- Added the ability to substitute variables with the environment of the service.

Misc
----

- Declared compatibility with Python 3.13.
