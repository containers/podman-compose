# Contributing to podman-compose

## Who can contribute? 

- Users that found a bug
- Users that wants to propose new functionalities or enhancements
- Users that want to help other users to troubleshoot their environments
- Developers that want to fix bugs
- Developers that want to implement new functionalities or enhancements

## Branches

Please request your PR to be merged into the `devel` branch. 
Changes to the `stable` branch are managed by the repository maintainers.

## Development environment setup

Note: Some steps are OPTIONAL but all are RECOMMENDED.

1. Fork the project repo and clone it
```shell
$ git clone https://github.com/USERNAME/podman-compose.git
$ cd podman-compose
```
1. (OPTIONAL) Create a python virtual environment. Example using [virtualenv wrapper](https://virtualenvwrapper.readthedocs.io/en/latest/): 
```shell
mkvirtualenv podman-compose
```
2. Install the project runtime and development requirements   
```shell
$ pip install '.[devel]'
```
3. (OPTIONAL) Install `pre-commit` git hook scripts (https://pre-commit.com/#3-install-the-git-hook-scripts)
```shell
$ pre-commit install
```
4. Create a new branch, develop and add tests when possible
5. Run linting & testing before committing code. Ensure all the hooks are passing.
```shell
$ pre-commit run --all-files
```
6. Run code coverage
```shell
coverage run --source podman_compose -m unittest pytests/*.py
python -m unittest tests/*.py
coverage combine
coverage report
coverage html
```
7. Commit your code to your fork's branch. 
   - Make sure you include a `Signed-off-by` message in your commits. Read [this guide](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits) to learn how to sign your commits 
   - In the commit message reference the Issue ID that your code fixes and a brief description of the changes. Example: `Fixes #516: allow empty network`
7. Open a PR to `containers/podman-compose:devel` and wait for a maintainer to review your work.

## Adding new commands

To add a command you need to add a function that is decorated
with `@cmd_run` passing the compose instance, command name and
description. This function must be declared `async` the wrapped 
function should accept two arguments the compose instance and 
the command-specific arguments (resulted from python's `argparse` 
package) inside that command you can run PodMan like this 
`await compose.podman.run(['inspect', 'something'])`and inside 
that function you can access `compose.pods` and `compose.containers` 
...etc. Here is an example

```
@cmd_run(podman_compose, 'build', 'build images defined in the stack')
async def compose_build(compose, args):
    await compose.podman.run(['build', 'something'])
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
async def compose_up(compose, args):
    await compose.commands['down'](compose, args)
    # or
    await compose.commands['down'](argparse.Namespace(foo=123))
```


## Missing Commands (help needed)
```
  bundle             Generate a Docker bundle from the Compose file
  config             Validate and view the Compose file
  create             Create services
  events             Receive real time events from containers
  images             List images
  logs               View output from containers
  port               Print the public port for a port binding
  ps                 List containers
  rm                 Remove stopped containers
  run                Run a one-off command
  scale              Set number of containers for a service
  top                Display the running processes
```
