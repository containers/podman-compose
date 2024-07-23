# SPDX-License-Identifier: GPL-2.0

import os
import unittest

from parameterized import parameterized

from podman_compose import container_to_args
from tests.unit.test_container_to_args import create_compose_mock
from tests.unit.test_container_to_args import get_minimal_container


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


class TestContainerToArgsSecrets(unittest.IsolatedAsyncioTestCase):
    async def test_pass_secret_as_env_variable(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret": {"external": "true"}  # must have external or name value
        }

        cnt = get_minimal_container()
        cnt["secrets"] = [
            {
                "source": "my_secret",
                "target": "ENV_SECRET",
                "type": "env",
            },
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--secret",
                "my_secret,type=env,target=ENV_SECRET",
                "busybox",
            ],
        )

    async def test_secret_as_env_external_true_has_no_name(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret": {
                "name": "my_secret",  # must have external or name value
            }
        }

        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            {
                "source": "my_secret",
                "target": "ENV_SECRET",
                "type": "env",
            }
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--secret",
                "my_secret,type=env,target=ENV_SECRET",
                "busybox",
            ],
        )

    async def test_pass_secret_as_env_variable_no_external(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret": {}  # must have external or name value
        }

        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            {
                "source": "my_secret",
                "target": "ENV_SECRET",
                "type": "env",
            }
        ]

        with self.assertRaises(ValueError) as context:
            await container_to_args(c, cnt)
        self.assertIn('ERROR: unparsable secret: ', str(context.exception))

    @parameterized.expand([
        (
            "secret_no_name",
            {"my_secret": "my_secret_name", "external": "true"},
            {},  # must have a name
        ),
        (
            "no_secret_name_in_declared_secrets",
            {},  # must have a name
            {
                "source": "my_secret_name",
            },
        ),
        (
            "secret_name_does_not_match_declared_secrets_name",
            {
                "wrong_name": "my_secret_name",
            },
            {
                "source": "name",  # secret name must match the one in declared_secrets
            },
        ),
        (
            "secret_name_empty_string",
            {"": "my_secret_name"},
            {
                "source": "",  # can not be empty string
            },
        ),
    ])
    async def test_secret_name(self, test_name, declared_secrets, add_to_minimal_container):
        c = create_compose_mock()
        c.declared_secrets = declared_secrets

        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [add_to_minimal_container]

        with self.assertRaises(ValueError) as context:
            await container_to_args(c, cnt)
        self.assertIn('ERROR: undeclared secret: ', str(context.exception))

    async def test_secret_string_no_external_name_in_declared_secrets(self):
        c = create_compose_mock()
        c.declared_secrets = {"my_secret_name": {"external": "true"}}
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            "my_secret_name",
        ]
        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--secret",
                "my_secret_name",
                "busybox",
            ],
        )

    async def test_secret_string_options_external_name_in_declared_secrets(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret_name": {
                "external": "true",
                "name": "my_secret_name",
            }
        }
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            {
                "source": "my_secret_name",
                "target": "my_secret_name",
                "uid": "103",
                "gid": "103",
                "mode": "400",
            }
        ]

        with self.assertLogs() as cm:
            args = await container_to_args(c, cnt)
        self.assertEqual(len(cm.output), 1)
        self.assertIn('That is un-supported and a no-op and is ignored.', cm.output[0])
        self.assertIn('my_secret_name', cm.output[0])

        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--secret",
                "my_secret_name,uid=103,gid=103,mode=400",
                "busybox",
            ],
        )

    async def test_secret_string_external_name_in_declared_secrets_does_not_match_secret(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret_name": {
                "external": "true",
                "name": "wrong_secret_name",
            }
        }
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            "my_secret_name",
        ]

        with self.assertRaises(ValueError) as context:
            await container_to_args(c, cnt)
        self.assertIn('ERROR: Custom name/target reference ', str(context.exception))

    async def test_secret_target_does_not_match_secret_name_secret_type_not_env(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret_name": {
                "external": "true",
            }
        }
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            {
                "source": "my_secret_name",
                "target": "does_not_equal_secret_name",
                "type": "does_not_equal_env",
            }
        ]

        with self.assertRaises(ValueError) as context:
            await container_to_args(c, cnt)
        self.assertIn('ERROR: Custom name/target reference ', str(context.exception))

    async def test_secret_target_does_not_match_secret_name_secret_type_env(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret_name": {
                "external": "true",
            }
        }
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            {"source": "my_secret_name", "target": "does_not_equal_secret_name", "type": "env"}
        ]

        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--secret",
                "my_secret_name,type=env,target=does_not_equal_secret_name",
                "busybox",
            ],
        )

    async def test_secret_target_matches_secret_name_secret_type_not_env(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "my_secret_name": {
                "external": "true",
            }
        }
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            {"source": "my_secret_name", "target": "my_secret_name", "type": "does_not_equal_env"}
        ]

        with self.assertLogs() as cm:
            args = await container_to_args(c, cnt)
        self.assertEqual(len(cm.output), 1)
        self.assertIn('That is un-supported and a no-op and is ignored.', cm.output[0])
        self.assertIn('my_secret_name', cm.output[0])

        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--secret",
                "my_secret_name,type=does_not_equal_env",
                "busybox",
            ],
        )

    @parameterized.expand([
        (
            "no_secret_target",
            {
                "file_secret": {
                    "file": "./my_secret",
                }
            },
            "file_secret",
            repo_root() + "/test_dirname/my_secret:/run/secrets/file_secret:ro,rprivate,rbind",
        ),
        (
            "custom_target_name",
            {
                "file_secret": {
                    "file": "./my_secret",
                }
            },
            {
                "source": "file_secret",
                "target": "custom_name",
            },
            repo_root() + "/test_dirname/my_secret:/run/secrets/custom_name:ro,rprivate,rbind",
        ),
        (
            "no_custom_target_name",
            {
                "file_secret": {
                    "file": "./my_secret",
                }
            },
            {
                "source": "file_secret",
            },
            repo_root() + "/test_dirname/my_secret:/run/secrets/file_secret:ro,rprivate,rbind",
        ),
        (
            "custom_location",
            {
                "file_secret": {
                    "file": "./my_secret",
                }
            },
            {
                "source": "file_secret",
                "target": "/etc/custom_location",
            },
            repo_root() + "/test_dirname/my_secret:/etc/custom_location:ro,rprivate,rbind",
        ),
    ])
    async def test_file_secret(
        self, test_name, declared_secrets, add_to_minimal_container, expected_volume_ref
    ):
        c = create_compose_mock()
        c.declared_secrets = declared_secrets
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [add_to_minimal_container]
        args = await container_to_args(c, cnt)
        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--volume",
                expected_volume_ref,
                "busybox",
            ],
        )

    async def test_file_secret_unused_params_warning(self):
        c = create_compose_mock()
        c.declared_secrets = {
            "file_secret": {
                "file": "./my_secret",
            }
        }
        cnt = get_minimal_container()
        cnt["_service"] = "test-service"
        cnt["secrets"] = [
            {
                "source": "file_secret",
                "target": "unused_params_warning",
                "uid": "103",
                "gid": "103",
                "mode": "400",
            }
        ]
        with self.assertLogs() as cm:
            args = await container_to_args(c, cnt)
        self.assertEqual(len(cm.output), 1)
        self.assertIn('with uid, gid, or mode.', cm.output[0])
        self.assertIn('unused_params_warning', cm.output[0])

        self.assertEqual(
            args,
            [
                "--name=project_name_service_name1",
                "-d",
                "--network=bridge",
                "--network-alias=service_name",
                "--volume",
                repo_root()
                + "/test_dirname/my_secret:/run/secrets/unused_params_warning:ro,rprivate,rbind",
                "busybox",
            ],
        )
