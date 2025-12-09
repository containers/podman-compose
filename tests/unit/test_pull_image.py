from argparse import Namespace
from unittest import IsolatedAsyncioTestCase
from unittest import mock

from parameterized import parameterized

from podman_compose import PullImageSettings
from podman_compose import pull_image
from podman_compose import pull_images
from podman_compose import settings_to_pull_args


class TestPullImageSettings(IsolatedAsyncioTestCase):
    def test_unsupported_policy_fallback_to_missing(self) -> None:
        settings = PullImageSettings("localhost/test:1", policy="unsupported")
        assert settings.policy == "missing"

    def test_update_policy(self) -> None:
        settings = PullImageSettings("localhost/test:1", policy="never")
        assert settings.policy == "never"

        # not supported policy
        settings.update_policy("unsupported")
        assert settings.policy == "never"

        settings.update_policy("missing")
        assert settings.policy == "missing"

        settings.update_policy("newer")
        assert settings.policy == "newer"

        settings.update_policy("always")
        assert settings.policy == "always"

        # Ensure policy is not downgraded
        settings.update_policy("build")
        assert settings.policy == "always"

    def test_pull_args(self) -> None:
        settings = PullImageSettings("localhost/test:1", policy="always", quiet=True)
        assert settings_to_pull_args(settings) == [
            "--policy",
            "always",
            "--quiet",
            "localhost/test:1",
        ]

        settings.quiet = False
        assert settings_to_pull_args(settings) == ["--policy", "always", "localhost/test:1"]

    @mock.patch("podman_compose.Podman")
    async def test_pull_success(self, podman_mock: mock.Mock) -> None:
        settings = PullImageSettings("localhost/test:1", policy="always", quiet=True)

        run_mock = mock.AsyncMock(return_value=0)
        podman_mock.run = run_mock

        result = await pull_image(podman_mock, settings)
        assert result == 0
        run_mock.assert_called_once_with(
            [], "pull", ["--policy", "always", "--quiet", "localhost/test:1"]
        )

    @mock.patch("podman_compose.Podman")
    async def test_pull_failed(self, podman_mock: mock.Mock) -> None:
        settings = PullImageSettings(
            "localhost/test:1",
            policy="always",
            quiet=True,
            ignore_pull_error=True,
        )

        podman_mock.run = mock.AsyncMock(return_value=1)

        # with ignore_pull_error=True, should return 0 even if pull fails
        result = await pull_image(podman_mock, settings)
        assert result == 0

        # with ignore_pull_error=False, should return the actual error code
        settings.ignore_pull_error = False
        result = await pull_image(podman_mock, settings)
        assert result == 1

    @mock.patch("podman_compose.Podman")
    async def test_pull_with_never_policy(self, podman_mock: mock.Mock) -> None:
        settings = PullImageSettings(
            "localhost/test:1",
            policy="never",
            quiet=True,
            ignore_pull_error=True,
        )

        run_mock = mock.AsyncMock(return_value=1)
        podman_mock.run = run_mock

        result = await pull_image(podman_mock, settings)
        assert result == 0
        assert run_mock.call_count == 0

    @parameterized.expand([
        (
            "Local image should not pull",
            [{"image": "localhost/a:latest"}],
            [],
        ),
        (
            "Remote image should pull",
            [{"image": "ghcr.io/a:latest"}],
            [
                mock.call([], "pull", ["--policy", "missing", "ghcr.io/a:latest"]),
            ],
        ),
        (
            "The same image in service should call once",
            [
                {"image": "ghcr.io/a:latest"},
                {"image": "ghcr.io/a:latest"},
                {"image": "ghcr.io/b:latest"},
            ],
            [
                mock.call([], "pull", ["--policy", "missing", "ghcr.io/a:latest"]),
                mock.call([], "pull", ["--policy", "missing", "ghcr.io/b:latest"]),
            ],
        ),
    ])
    @mock.patch("podman_compose.Podman")
    async def test_pull_image(
        self,
        desc: str,
        services: list[dict],
        calls: list,
        podman_mock: mock.Mock,
    ) -> None:
        run_mock = mock.AsyncMock(return_value=1)
        podman_mock.run = run_mock

        assert await pull_images(podman_mock, Namespace(), services) == 0
        assert run_mock.call_count == len(calls)
        if calls:
            run_mock.assert_has_calls(calls, any_order=True)

    @mock.patch("podman_compose.Podman")
    async def test_pull_image_with_build_section(
        self,
        podman_mock: mock.Mock,
    ) -> None:
        run_mock = mock.AsyncMock(return_value=1)
        podman_mock.run = run_mock

        assert (
            await pull_images(
                podman_mock,
                Namespace(),
                [
                    {"image": "ghcr.io/a:latest", "build": {"context": "."}},
                ],
            )
            == 0
        )
        assert run_mock.call_count == 1
        run_mock.assert_called_with([], "pull", ["--policy", "missing", "ghcr.io/a:latest"])
