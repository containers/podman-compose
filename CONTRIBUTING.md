# Contributing to podman-compose

## Development guidelines

### Always run tests

All tests must pass on each commit to help bisecting. If you're doing TDD, commit
the test afterwards.

The following is the set of tests to run:
```
ruff format
ruff check --fix
mypy .
pylint podman_compose.py
python -m unittest discover tests/unit
python -m unittest discover -v tests/integration  # takes a while to run
```

### Committing guidelines

Add one change per commit. If you're refactoring and adding functionality, this should be at least 2
commits. If you want to add `and` to commit message - this is good indication that commits needed
splitting.

Commits must be complete. If there are commits that only fix previous commits, they should be
squashed together. Otherwise they just confuse the reviewer.

Do not add `feat:` or `fix:` prefixes to commit messages.

Commits require a `Signed-off-by` message ([guide](https://github.com/containers/common/blob/main/CONTRIBUTING.md#sign-your-prs)).
If you forget to add this message, run `git rebase main --signoff`.

### PR description

If PR adds a new feature that improves compatibility with docker-compose, please add a link
to the exact part of compose spec that the PR touches.

### Release notes

If your change is user-facing - fixing a bug or adding a new feature, then a release note must
be added to newsfragment/ directory. Check out docs/Changelog-1.4.0.md for examples of how
a release note should look like.

### Tests

All changes require tests.

Use `nopush/podman-compose-test` image in integration test dockerfiles. This is to reduce the
number of pulls Github CI does during a test run.

## Development environment setup

1. Fork the project repository and clone it:

   ```shell
   $ git clone https://github.com/USERNAME/podman-compose.git
   $ cd podman-compose
   ```

2. Create a Python virtual environment and install project requirements.
   Example using python builtin `venv` module:

    ```shell
    $ python3 -m venv .venv
    $ . .venv/bin/activate
    $ pip install '.[devel]'
    ```

3. (OPTIONAL) Install `pre-commit` git hook scripts
   (https://pre-commit.com/#3-install-the-git-hook-scripts):

   ```shell
   $ pre-commit install
   ```

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
