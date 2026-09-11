# SPDX-License-Identifier: GPL-2.0

import os
import subprocess
import unittest
from unittest import mock

from podman_compose import PodmanComposeError
from podman_compose import create_secrets_from_environment
from tests.unit.test_container_to_args import create_compose_mock


class TestCreateSecretsFromEnvironment(unittest.IsolatedAsyncioTestCase):
    async def test_no_declared_secrets(self) -> None:
        c = create_compose_mock()
        c.declared_secrets = None
        c.podman.output = mock.AsyncMock()
        c.podman.run = mock.AsyncMock()

        await create_secrets_from_environment(c)
        c.podman.output.assert_not_called()
        c.podman.run.assert_not_called()

        c.declared_secrets = {}
        await create_secrets_from_environment(c)
        c.podman.output.assert_not_called()
        c.podman.run.assert_not_called()

    async def test_declared_secrets_without_environment(self) -> None:
        c = create_compose_mock()
        c.declared_secrets = {
            "file_secret": {"file": "./my_secret"},
            "external_secret": {"external": True},
        }
        c.podman.output = mock.AsyncMock()
        c.podman.run = mock.AsyncMock()

        await create_secrets_from_environment(c)
        c.podman.output.assert_not_called()
        c.podman.run.assert_not_called()

    async def test_environment_variable_not_set_raises_value_error(self) -> None:
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret": {"environment": "UNSET_SECRET_ENV_VAR"},
        }
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                await create_secrets_from_environment(c)
            self.assertIn(
                "Environment variable 'UNSET_SECRET_ENV_VAR' required"
                + " by secret 'my_secret' is not set",
                str(context.exception),
            )

    async def test_create_new_secret_when_not_exists(self) -> None:
        c = create_compose_mock(project_name="my_project")
        c.declared_secrets = {
            "my_secret": {"environment": "MY_SECRET_ENV_VAR"},
        }

        async def podman_output(*args: object, **kwargs: object) -> bytes:
            raise subprocess.CalledProcessError(1, "secret exists")

        c.podman.output = mock.AsyncMock(side_effect=podman_output)
        c.podman.run = mock.AsyncMock(return_value=0)

        with mock.patch.dict(os.environ, {"MY_SECRET_ENV_VAR": "secret_value"}):
            await create_secrets_from_environment(c)

        c.podman.output.assert_called_once_with([], "secret", ["exists", "my_project_my_secret"])
        c.podman.run.assert_called_once_with(
            [],
            "secret",
            [
                "create",
                "--label",
                "io.podman.compose.project=my_project",
                "--replace",
                "--env",
                "my_project_my_secret",
                "MY_SECRET_ENV_VAR",
            ],
        )

    async def test_replace_existing_secret_managed_by_compose(self) -> None:
        c = create_compose_mock(project_name="my_project")
        c.declared_secrets = {
            "my_secret": {"environment": "MY_SECRET_ENV_VAR"},
        }

        async def podman_output(*args: object, **kwargs: object) -> bytes:
            cmd = args[2]
            if cmd == ["exists", "my_project_my_secret"]:
                return b""
            if cmd == [
                "inspect",
                "--format",
                '{{index .Spec.Labels "io.podman.compose.project"}}',
                "my_project_my_secret",
            ]:
                return b"my_project\n"
            raise ValueError(f"Unexpected command: {cmd}")

        c.podman.output = mock.AsyncMock(side_effect=podman_output)
        c.podman.run = mock.AsyncMock(return_value=0)

        with mock.patch.dict(os.environ, {"MY_SECRET_ENV_VAR": "new_secret_value"}):
            await create_secrets_from_environment(c)

        self.assertEqual(c.podman.output.call_count, 2)
        c.podman.run.assert_called_once_with(
            [],
            "secret",
            [
                "create",
                "--label",
                "io.podman.compose.project=my_project",
                "--replace",
                "--env",
                "my_project_my_secret",
                "MY_SECRET_ENV_VAR",
            ],
        )

    async def test_existing_secret_not_managed_by_compose_raises_error(self) -> None:
        c = create_compose_mock(project_name="my_project")
        c.declared_secrets = {
            "my_secret": {"environment": "MY_SECRET_ENV_VAR"},
        }

        async def podman_output(*args: object, **kwargs: object) -> bytes:
            cmd = args[2]
            if cmd == ["exists", "my_project_my_secret"]:
                return b""
            if cmd == [
                "inspect",
                "--format",
                '{{index .Spec.Labels "io.podman.compose.project"}}',
                "my_project_my_secret",
            ]:
                return b"other_project\n"
            raise ValueError(f"Unexpected command: {cmd}")

        c.podman.output = mock.AsyncMock(side_effect=podman_output)
        c.podman.run = mock.AsyncMock(return_value=0)

        with mock.patch.dict(os.environ, {"MY_SECRET_ENV_VAR": "secret_value"}):
            with self.assertRaises(PodmanComposeError) as context:
                await create_secrets_from_environment(c)

            self.assertIn(
                "Secret my_project_my_secret already exists, but is missing the label "
                + "indicating it's managed by compose.",
                str(context.exception),
            )
            self.assertIn(
                "Expected: 'io.podman.compose.project=my_project', got 'other_project'",
                str(context.exception),
            )
            self.assertIn("Refusing to overwrite.", str(context.exception))

        c.podman.run.assert_not_called()

    async def test_multiple_environment_secrets(self) -> None:
        c = create_compose_mock(project_name="test_proj")
        c.declared_secrets = {
            "sec1": {"environment": "ENV_VAR_1"},
            "file_sec": {"file": "./path"},
            "sec2": {"environment": "ENV_VAR_2"},
        }

        async def podman_output(*args: object, **kwargs: object) -> bytes:
            cmd = args[2]
            if cmd == ["exists", "test_proj_sec1"]:
                return b""
            if cmd == [
                "inspect",
                "--format",
                '{{index .Spec.Labels "io.podman.compose.project"}}',
                "test_proj_sec1",
            ]:
                return b"test_proj\n"
            if cmd == ["exists", "test_proj_sec2"]:
                raise subprocess.CalledProcessError(1, "secret exists")
            raise ValueError(f"Unexpected command: {cmd}")

        c.podman.output = mock.AsyncMock(side_effect=podman_output)
        c.podman.run = mock.AsyncMock(return_value=0)

        with mock.patch.dict(os.environ, {"ENV_VAR_1": "val1", "ENV_VAR_2": "val2"}):
            await create_secrets_from_environment(c)

        self.assertEqual(c.podman.run.call_count, 2)
        c.podman.run.assert_any_call(
            [],
            "secret",
            [
                "create",
                "--label",
                "io.podman.compose.project=test_proj",
                "--replace",
                "--env",
                "test_proj_sec1",
                "ENV_VAR_1",
            ],
        )
        c.podman.run.assert_any_call(
            [],
            "secret",
            [
                "create",
                "--label",
                "io.podman.compose.project=test_proj",
                "--replace",
                "--env",
                "test_proj_sec2",
                "ENV_VAR_2",
            ],
        )
