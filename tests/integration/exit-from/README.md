We have service named sh1 that exits with code 1 and sh2 that exists with code 2

```
podman-compose up --exit-code-from=sh1
echo $?
```

the above should give 1.

```
podman-compose up --exit-code-from=sh2
echo $?
```

the above should give 2.
