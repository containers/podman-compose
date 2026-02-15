# Echo Service example

```
podman-compose up
```

Test the service with curl like this:

```
$ curl -X POST -d "foobar" http://localhost:8080/; echo

CLIENT VALUES:
client_address=10.89.31.2
command=POST
real path=/
query=nil
request_version=1.1
request_uri=http://localhost:8080/

SERVER VALUES:
server_version=nginx: 1.10.0 - lua: 10001

HEADERS RECEIVED:
accept=*/*
content-length=6
content-type=application/x-www-form-urlencoded
host=localhost:8080
user-agent=curl/7.76.1
BODY:
foobar
```
