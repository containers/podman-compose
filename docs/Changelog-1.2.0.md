Version v1.2.0 (2024-06-26)
===========================

Bug fixes
---------

- Fixed handling of `--in-pod` argument. Previously it was hard to provide false value to it.
- podman-compose no longer creates pods when registering systemd unit.
- Fixed warning `RuntimeWarning: coroutine 'create_pods' was never awaited`
- Fixed error when setting up IPAM network with default driver.
- Fixed support for having list and dictionary `depends_on` sections in related compose files.
- Fixed logging of failed build message.
- Fixed support for multiple entries in `include` section.
- Fixed environment variable precedence order.

Changes
-------

- `x-podman` dictionary in container root has been migrated to `x-podman.*` fields in container root.

New features
------------

- Added support for `--publish` in `podman-compose run`.
- Added support for Podman external root filesystem management (`--rootfs` option).
- Added support for `podman-compose images` command.
- Added support for `env_file` being configured via dictionaries.
- Added support for enabling GPU access.
- Added support for selinux in verbose mount specification.
- Added support for `additional_contexts` section.
- Added support for multi-line environment files.
- Added support for passing contents of `podman-compose.yml` via stdin.
- Added support for specifying the value for `--in-pod` setting in `podman-compose.yml` file.
- Added support for environment secrets.

Documentation
-------------

- Added instructions on how to install podman-compose on Homebrew.
- Added explanation that netavark is an alternative to dnsname plugin
