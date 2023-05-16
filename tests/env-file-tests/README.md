running the following commands should always give podman-rocks-123

```
podman-compose -f project/container-compose.yaml --env-file env-files/project-1.env up
```

```
podman-compose -f $(pwd)/project/container-compose.yaml --env-file $(pwd)/env-files/project-1.env up
```
