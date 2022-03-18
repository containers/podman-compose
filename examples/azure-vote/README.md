# Azure Vote Example

This example have two containers:

* backend: `redis` used as storage
* frontend: having supervisord, nginx, uwsgi/python


```
echo "HOST_PORT=8080" > .env
podman-compose up
```

after typing the commands above open your browser on the host port you picked above like
[http://localhost:8080/](http://localhost:8080/)


