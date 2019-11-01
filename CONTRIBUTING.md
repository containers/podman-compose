# Contributing to podman-compose

## Adding new commands

To add a command you need to add a function that is decorated
with `@cmd_run` passing the compose instance, command name and
description. the wrapped function should accept two arguments
the compose instance and the command-specific arguments (resulted
from python's `argparse` package) inside that command you can
run PodMan like this `compose.podman.run(['inspect', 'something'])`
and inside that function you can access `compose.pods`
and `compose.containers` ...etc.
Here is an example

```
@cmd_run(podman_compose, 'build', 'build images defined in the stack')
def compose_build(compose, args):
    compose.podman.run(['build', 'something'])
```

## Command arguments parsing

Add a function that accept `parser` which is an instance from `argparse`.
In side that function you can call `parser.add_argument()`.
The function decorated with `@cmd_parse` accepting the compose instance,
and command names (as a list or as a string).
You can do this multiple times. 

Here is an example

```
@cmd_parse(podman_compose, 'build')
def compose_build_parse(parser):
    parser.add_argument("--pull",
        help="attempt to pull a newer version of the image", action='store_true')
    parser.add_argument("--pull-always",
        help="attempt to pull a newer version of the image, Raise an error even if the image is present locally.", action='store_true')
```

NOTE: `@cmd_parse` should be after `@cmd_run`

## Calling a command from inside another

If you need to call `podman-compose down` from inside `podman-compose up`
do something like:

```
@cmd_run(podman_compose, 'up', 'up desc')
def compose_up(compose, args):
    compose.commands['down'](compose, args)
    # or
    compose.commands['down'](argparse.Namespace(foo=123))
```


## Missing Commands (help needed)

  Command name     | Command description
  ---              | ---
  bundle           | Generate a Docker bundle from the Compose file
  config           | Validate and view the Compose file
  create           | Create services
  events           | Receive real time events from containers
  exec             | Execute a command in a running container
  images           | List images
  kill             | Kill containers
  logs             | View output from containers
  pause            | Pause services
  port             | Print the public port for a port binding
  ps               | List containers
  rm               | Remove stopped containers
  run              | Run a one-off command
  scale            | Set number of containers for a service
  top              | Display the running processes
  unpause          | Unpause services
  version          | Show the Docker-Compose version information
