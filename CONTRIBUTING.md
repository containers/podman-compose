# Contributing to podman-compose

## Who can contribute?

- Users that found a bug,
- Users that want to propose new functionalities or enhancements,
- Users that want to help other users to troubleshoot their environments,
- Developers that want to fix bugs,
- Developers that want to implement new functionalities or enhancements.

## Development environment setup

Note: Some steps are OPTIONAL but all are RECOMMENDED.

1. Fork the project repository and clone it:

   ```shell
   $ git clone https://github.com/USERNAME/podman-compose.git
   $ cd podman-compose
   ```

2. (OPTIONAL) Create a Python virtual environment. Example using python builtin
   `venv` module:

    ```shell
    $ python3 -m venv .venv
    $ . .venv/bin/activate
    ```

3. Install the project runtime and development requirements:

   ```shell
   $ pip install '.[devel]'
   ```

4. (OPTIONAL) Install `pre-commit` git hook scripts
   (https://pre-commit.com/#3-install-the-git-hook-scripts):

   ```shell
   $ pre-commit install
   ```

5. Create a new branch, develop and add tests when possible.
6. Run linting and testing before committing code. Ensure all the hooks are passing.

   ```shell
   $ pre-commit run --all-files
   ```

7. Run code coverage:

    ```shell
    $ coverage run --source podman_compose -m unittest discover tests/unit
    $ python3 -m unittest discover tests/integration
    $ coverage combine
    $ coverage report
    $ coverage html
    ```

8. Commit your code to your fork's branch.
   - Make sure you include a `Signed-off-by` message in your commits.
     Read [this guide](https://github.com/containers/common/blob/main/CONTRIBUTING.md#sign-your-prs)
     to learn how to sign your commits.
   - In the commit message body, reference the Issue ID that your code fixes and a brief description of the changes.
     Example:
     ```
     Allow empty network

     <description, such as links to the compose spec and so on>

     Fixes https://github.com/containers/podman-compose/issues/516
     ```
   - If your commit requires a refactoring, first do the refactoring and
     commit it separately before starting feature work. This makes the
     pull request easier to review. Additionally, pull request will be
     less risky, because if it breaks something, it's way easier to
     isolate the offending code, understand what's broken and fix it.
     Due to the latter reason it's best to commit in as many independent
     commits as reasonable.

     This will result in pull requests being merged much faster.

9. Open a pull request to `containers/podman-compose` and wait for a maintainer to review your work.

## Adding new commands

To add a command, you need to add a function that is decorated with `@cmd_run`.

The decorated function must be declared `async` and should accept two arguments: The compose
instance and the command-specific arguments (resulting from Python's `argparse` package).

In this function, you can run Podman (e.g. `await compose.podman.run(['inspect', 'something'])`),
access `compose.pods`, `compose.containers` etc.

Here is an example:

```python
@cmd_run(podman_compose, 'build', 'build images defined in the stack')
async def compose_build(compose, args):
    await compose.podman.run(['build', 'something'])
```

## Command arguments parsing

To add arguments to be parsed by a command, you need to add a function that is decorated with
`@cmd_parse` which accepts the compose instance and the command's name (as a string list or as a
single string).

The decorated function should accept a single argument: An instance of `argparse`.

In this function, you can call `parser.add_argument()` to add a new argument to the command.

Note you can add such a function multiple times.

Here is an example:

```python
@cmd_parse(podman_compose, 'build')
def compose_build_parse(parser):
    parser.add_argument("--pull",
        help="attempt to pull a newer version of the image", action='store_true')
    parser.add_argument("--pull-always",
        help="Attempt to pull a newer version of the image, "
             "raise an error even if the image is present locally.",
        action='store_true')
```

NOTE: `@cmd_parse` should be after `@cmd_run`.

## Calling a command from another one

If you need to call `podman-compose down` from `podman-compose up`, do something like:

```python
@cmd_run(podman_compose, 'up', 'up desc')
async def compose_up(compose, args):
    await compose.commands['down'](compose, args)
    # or
    await compose.commands['down'](argparse.Namespace(foo=123))
```

## Missing Commands (help needed)

```
  bundle             Generate a Docker bundle from the Compose file
  create             Create services
  events             Receive real time events from containers
  images             List images
  rm                 Remove stopped containers
  scale              Set number of containers for a service
  top                Display the running processes
```
