Version v1.1.0 (2024-04-17)
===========================

Bug fixes
---------

- Fixed support for values with equals sign in `-e` argument of `run` and `exec` commands.
- Fixed duplicate arguments being emitted in `stop` and `restart` commands.
- Removed extraneous debug output. `--verbose` flag has been added to preserve verbose output.
- Links aliases are now added to service aliases.
- Fixed image build process to use defined environment variables.
- Empty list is now allowed to be `COMMAND` and `ENTRYPOINT`.
- Environment files are now resolved relative to current working directory.
- Exit code of container build is now preserved as return code of `build` command.

New features
------------

- Added support for `uidmap`, `gidmap`, `http_proxy` and `runtime` service configuration keys.
- Added support for `enable_ipv6` network configuration key.
- Added `--parallel` option to support parallel pulling and building of images.
- Implemented support for maps in `sysctls` container configuration key.
- Implemented `stats` command.
- Added `--no-normalize` flag to `config` command.
- Added support for `include` global configuration key.
- Added support for `build` command.
- Added support to start containers with multiple networks.
- Added support for `profile` argument.
- Added support for starting podman in existing network namespace.
- Added IPAM driver support. 
- Added support for file secrets being passed to `podman build` via `--secret` argument.
- Added support for multiple networks with separately specified IP and MAC address.
- Added support for `service.build.ulimits` when building image.
