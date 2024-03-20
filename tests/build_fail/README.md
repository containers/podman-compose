# Test podman-compose with build (fail scenario)

```shell
podman-compose build || echo $?
```

expected output would be something like

```
STEP 1/3: FROM busybox
STEP 2/3: RUN this_command_does_not_exist
/bin/sh: this_command_does_not_exist: not found
Error: building at STEP "RUN this_command_does_not_exist": while running runtime: exit status 127

exit code: 127
```

Expected `podman-compose` exit code:
```shell
echo $?
127
```
