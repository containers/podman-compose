# Test compose environment variables

Run from this directory:

```sh
THIS_VARIABLE_SHOULD_BE_SET_BY_SHELL=SUCCESS podman-compose up
```

Ensure that the following environment variables are set inside the `print_env`
service container:

```
THIS_VARIABLE_SHOULD_BE_SET=SUCCESS
THIS_VARIABLE_SHOULD_BE_SET_BY_SHELL=SUCCESS
THIS_VARIABLE_SHOULD_BE_SET_TOO=SUCCESS

```

In the successful case, you should see logs like this:

```
podman start -a environment_print_env_1
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TERM=xterm
HOSTNAME=cafebadcafe
container=podman
THIS_VARIABLE_SHOULD_BE_SET=SUCCESS
THIS_VARIABLE_SHOULD_BE_SET_BY_SHELL=SUCCESS
THIS_VARIABLE_SHOULD_BE_SET_TOO=SUCCESS
HOME=/root
```

Remember to run `podman-compose down` to clean up afterwards!
