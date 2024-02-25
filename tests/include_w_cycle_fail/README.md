# Test podman-compose with include cycle (fail scenario)

```shell
podman-compose up || echo $?
```

expected output would be something like

```
Compose file contains a cyclic chain of file includes: docker-compose.base-2.yaml

exit code: 1
```

Expected `podman-compose` exit code:
```shell
echo $?
1
```
