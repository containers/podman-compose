running the following commands should always give podman-rocks-123

```
podman-compose -f project/container-compose.yaml --env-file env-files/project-1.env up
```

```
podman-compose -f $(pwd)/project/container-compose.yaml --env-file $(pwd)/env-files/project-1.env up
```

```
podman-compose -f $(pwd)/project/container-compose.env-file-flat.yaml up
```

```
podman-compose -f $(pwd)/project/container-compose.env-file-obj.yaml up
```

```
podman-compose -f $(pwd)/project/container-compose.env-file-obj-optional.yaml up
```

based on environment variable precedent this command should give podman-rocks-321

```
ZZVAR1=podman-rocks-321 podman-compose -f $(pwd)/project/container-compose.yaml --env-file $(pwd)/env-files/project-1.env up
```

_The below test should print three environment variables_

```
podman-compose -f $(pwd)/project/container-compose.load-.env-in-project.yaml run --rm app

ZZVAR1=This value is overwritten by env-file-tests/.env
ZZVAR2=This value is loaded from .env in project/ directory
ZZVAR3=This value is loaded from env-file-tests/.env
```
