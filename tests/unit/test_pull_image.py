from argparse import Namespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

from parameterized import parameterized

from podman_compose import PullImage


class TestPullImage(IsolatedAsyncioTestCase):
    def test_unsupported_policy_fallback_to_missing(self) -> None:
        pull_image = PullImage("localhost/test:1", policy="unsupported")
        assert pull_image.policy == "missing"

    def test_update_policy(self) -> None:
        pull_image = PullImage("localhost/test:1", policy="never")
        assert pull_image.policy == "never"

        # not supported policy
        pull_image.update_policy("unsupported")
        assert pull_image.policy == "never"

        pull_image.update_policy("missing")
        assert pull_image.policy == "missing"

        pull_image.update_policy("newer")
        assert pull_image.policy == "newer"

        pull_image.update_policy("always")
        assert pull_image.policy == "always"

        # Ensure policy is not downgraded
        pull_image.update_policy("build")
        assert pull_image.policy == "always"

    def test_pull_args(self) -> None:
        pull_image = PullImage("localhost/test:1", policy="always", quiet=True)
        assert pull_image.pull_args == ["--policy", "always", "--quiet", "localhost/test:1"]

        pull_image.quiet = False
        assert pull_image.pull_args == ["--policy", "always", "localhost/test:1"]

    @patch("podman_compose.Podman")
    async def test_pull_success(self, podman_mock: Mock) -> None:
        pull_image = PullImage("localhost/test:1", policy="always", quiet=True)

        run_mock = AsyncMock()
        run_mock.return_value = 0
        podman_mock.run = run_mock

        result = await pull_image.pull(podman_mock)
        assert result == 0
        run_mock.assert_called_once_with(
            [], "pull", ["--policy", "always", "--quiet", "localhost/test:1"]
        )

    @patch("podman_compose.Podman")
    async def test_pull_failed(self, podman_mock: Mock) -> None:
        pull_image = PullImage(
            "localhost/test:1",
            policy="always",
            quiet=True,
            ignore_pull_error=True,
        )

        run_mock = AsyncMock()
        run_mock.return_value = 1
        podman_mock.run = run_mock

        # with ignore_pull_error=True, should return 0 even if pull fails
        result = await pull_image.pull(podman_mock)
        assert result == 0

        # with ignore_pull_error=False, should return the actual error code
        pull_image.ignore_pull_error = False
        result = await pull_image.pull(podman_mock)
        assert result == 1

    @patch("podman_compose.Podman")
    async def test_pull_with_never_policy(self, podman_mock: Mock) -> None:
        pull_image = PullImage(
            "localhost/test:1",
            policy="never",
            quiet=True,
            ignore_pull_error=True,
        )

        run_mock = AsyncMock()
        run_mock.return_value = 1
        podman_mock.run = run_mock

        result = await pull_image.pull(podman_mock)
        assert result == 0
        assert run_mock.call_count == 0

    @parameterized.expand([
        (
            "Local image should not pull",
            Namespace(),
            [{"image": "localhost/a:latest"}],
            0,
            [],
        ),
        (
            "Remote image should pull",
            Namespace(),
            [{"image": "ghcr.io/a:latest"}],
            1,
            [
                call([], "pull", ["--policy", "missing", "ghcr.io/a:latest"]),
            ],
        ),
        (
            "The same image in service should call once",
            Namespace(),
            [
                {"image": "ghcr.io/a:latest"},
                {"image": "ghcr.io/a:latest"},
                {"image": "ghcr.io/b:latest"},
            ],
            2,
            [
                call([], "pull", ["--policy", "missing", "ghcr.io/a:latest"]),
                call([], "pull", ["--policy", "missing", "ghcr.io/b:latest"]),
            ],
        ),
    ])
    @patch("podman_compose.Podman")
    async def test_pull_images(
        self,
        desc: str,
        args: Namespace,
        services: list[dict],
        call_count: int,
        calls: list,
        podman_mock: Mock,
    ) -> None:
        run_mock = AsyncMock()
        run_mock.return_value = 0
        podman_mock.run = run_mock

        assert await PullImage.pull_images(podman_mock, args, services) == 0
        assert run_mock.call_count == call_count
        if calls:
            run_mock.assert_has_calls(calls, any_order=True)

    @patch("podman_compose.Podman")
    async def test_pull_images_with_build_section(
        self,
        podman_mock: Mock,
    ) -> None:
        run_mock = AsyncMock()
        run_mock.return_value = 1
        podman_mock.run = run_mock

        args: Namespace = Namespace()
        services: list[dict] = [
            {"image": "ghcr.io/a:latest", "build": {"context": "."}},
        ]
        assert await PullImage.pull_images(podman_mock, args, services) == 0
        assert run_mock.call_count == 1
        run_mock.assert_called_with([], "pull", ["--policy", "missing", "ghcr.io/a:latest"])
