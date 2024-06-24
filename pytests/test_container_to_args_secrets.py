# SPDX-License-Identifier: GPL-2.0

import unittest

from podman_compose import container_to_args

from .test_container_to_args import create_compose_mock
from .test_container_to_args import get_minimal_container


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
