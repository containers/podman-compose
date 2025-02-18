- Do not close file descriptors when executing podman. This allows
  externally created file descriptors to be passed to containers.
  These file descriptors might have been created through
  [systemd socket activation](https://github.com/containers/podman/blob/main/docs/tutorials/socket_activation.md#socket-activation-of-containers).
