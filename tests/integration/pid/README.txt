This is the output of command "up -d" with corresponding "pid/docker-compose.yml" file:
WARN[0000] freezer not supported: openat2 /sys/fs/cgroup/machine.slice/libpod-SHA.scope/cgroup.freeze: no such file or directory
WARN[0000] lstat /sys/fs/cgroup/machine.slice/libpod-SHA.scope: no such file or directory
pid_serv_1

Command output corresponds to a closed (but not fixed) issue in "containers/podman":
https://github.com/containers/podman/issues/11784

The command was tested on:
podman-compose version 1.3.0
podman version 4.3.1

Operating System: Debian GNU/Linux 12 (bookworm)
