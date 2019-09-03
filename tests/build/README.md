# Test podman-compose with build

```
podman-compose build
podman-compose up -d
curl http://localhost:8080/index.txt
curl http://localhost:8000/index.txt
podman inspect my-busybox-httpd2 
podman-compose down
```

expected output would be something like

```
2019-09-03T15:16:38+0000
ALT buildno=2 port 8000 2019-09-03T15:16:38+0000
{
...
}
```

as you can see we were able to override buildno to be 2 instead of 1,
and httpd_port to 8000.

NOTE: build labels are not passed to `podman build`
