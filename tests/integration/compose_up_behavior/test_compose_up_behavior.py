# SPDX-License-Identifier: GPL-2.0

import json
import os
import unittest
from typing import Any

from packaging import version
from parameterized import parameterized

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import get_podman_version
from tests.integration.test_utils import podman_compose_path
from tests.integration.test_utils import test_path


def compose_yaml_path(scenario: str) -> str:
    return os.path.join(
        os.path.join(test_path(), "compose_up_behavior"), f"docker-compose_{scenario}.yaml"
    )


def remove_file_if_exists(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


class TestComposeUpBehavior(unittest.TestCase, RunSubprocessMixin):
    def get_existing_containers(self, scenario: str) -> dict[str, Any]:
        out, _ = self.run_subprocess_assert_returncode(
            [
                podman_compose_path(),
                "-f",
                compose_yaml_path(scenario),
                "ps",
                "--format",
                'json',
            ],
        )
        containers = json.loads(out)
        return {
            c.get("Names")[0]: {
                "name": c.get("Names")[0],
                "id": c.get("Id"),
                "service_name": c.get("Labels", {}).get("io.podman.compose.service", ""),
                "config_hash": c.get("Labels", {}).get("io.podman.compose.config-hash", ""),
                "exited": c.get("Exited"),
            }
            for c in containers
        }

    def get_image_id(self, image: str) -> str:
        out, _ = self.run_subprocess_assert_returncode([
            "podman",
            "image",
            "inspect",
            "-f",
            "{{.Id}}",
            image,
        ])
        return out.decode("utf-8").strip()

    @parameterized.expand([
        (
            "service_change_app",
            "service_change_base",
            ["up"],
            {"app"},
        ),
        (
            "service_change_app",
            "service_change_base",
            ["up", "app"],
            {"app"},
        ),
        (
            "service_change_app",
            "service_change_base",
            ["up", "db"],
            set(),
        ),
        (
            "service_change_db",
            "service_change_base",
            ["up"],
            {"db", "app"},
        ),
        (
            "service_change_db",
            "service_change_base",
            ["up", "app"],
            {"db", "app"},
        ),
        (
            "service_change_db",
            "service_change_base",
            ["up", "db"],
            {"db", "app"},
        ),
    ])
    def test_recreate_on_config_changed(
        self,
        change_to: str,
        running_scenario: str,
        command_args: list[str],
        expect_recreated_services: set[str],
    ) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(running_scenario), "up", "-d"],
            )

            original_containers = self.get_existing_containers(running_scenario)

            out, err = self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "--verbose",
                    "-f",
                    compose_yaml_path(change_to),
                    *command_args,
                    "-d",
                ],
            )

            new_containers = self.get_existing_containers(change_to)
            recreated_services = {
                c.get("service_name")
                for c in original_containers.values()
                if new_containers.get(c.get("name"), {}).get("id") != c.get("id")
            }

            self.assertEqual(
                recreated_services,
                expect_recreated_services,
                msg=f"Expected services to be recreated: {expect_recreated_services}, "
                f"but got: {recreated_services}, containers: "
                f"[{original_containers}, {new_containers}]",
            )
            self.assertTrue(
                all([c.get("exited") is False for c in new_containers.values()]),
                msg="Not all containers are running after up command",
            )

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(change_to),
                "down",
                "-t",
                "0",
            ])

    @parameterized.expand([
        (
            "service_change_base",
            ["up", "--force-recreate"],
            {"app", "db", "no_deps"},
        ),
        (
            "service_change_base",
            ["up", "--force-recreate", "app"],
            {"app"},
        ),
        (
            "service_change_base",
            ["up", "--force-recreate", "db"],
            {"db", "app"},
        ),
        (
            "service_change_base",
            ["up", "--force-recreate", "no_deps"],
            {"no_deps"},
        ),
        (
            "service_change_base",
            ["up", "--force-recreate", "--always-recreate-deps", "app"],
            {"app", "db"},
        ),
    ])
    def test_force_recreate_scoped_to_requested_services(
        self,
        running_scenario: str,
        command_args: list[str],
        expect_recreated_services: set[str],
    ) -> None:
        try:
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_yaml_path(running_scenario), "up", "-d"],
            )

            original_containers = self.get_existing_containers(running_scenario)

            self.run_subprocess_assert_returncode(
                [
                    podman_compose_path(),
                    "--verbose",
                    "-f",
                    compose_yaml_path(running_scenario),
                    *command_args,
                    "-d",
                ],
            )

            new_containers = self.get_existing_containers(running_scenario)
            recreated_services = {
                c.get("service_name")
                for c in original_containers.values()
                if new_containers.get(c.get("name"), {}).get("id") != c.get("id")
            }

            self.assertEqual(
                recreated_services,
                expect_recreated_services,
                msg=f"Expected services to be recreated: {expect_recreated_services}, "
                f"but got: {recreated_services}, containers: "
                f"[{original_containers}, {new_containers}]",
            )
            self.assertTrue(
                all([c.get("exited") is False for c in new_containers.values()]),
                msg="Not all containers are running after up command",
            )

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_yaml_path(running_scenario),
                "down",
                "-t",
                "0",
            ])

    @unittest.skipIf(
        get_podman_version() < version.parse("5.6.0"),
        "The image pull policy feature was only added as of Podman 5.6.0.",
    )
    def test_pull_only_if_image_missing(self) -> None:
        """Verify image is pulled because default pull policy is --missing"""

        compose_file = compose_yaml_path("default_pull_policy")
        image = "docker.io/library/alpine:latest"

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "up",
                "-d",
            ])

            # Remove image while container is still up
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "-f",
                image,
            ])

            # up container one more time, it sees missing images and pulls them again
            _, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "--verbose",
                "-f",
                compose_file,
                "up",
                "-d",
            ])

            # podman pull command is explicitly run before container teardown and now is
            # visible in --verbose output. After container teardown, podman create is called
            # and already has needed images available
            self.assertIn(b"podman pull --policy missing alpine:latest", error)

            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "ps",
            ])
            self.assertIn(b"compose_up_behavior_test_1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "-f",
                image,
            ])

    @unittest.skipIf(
        get_podman_version() < version.parse("5.6.0"),
        "The image pull policy feature was only added as of Podman 5.6.0.",
    )
    def test_pull_default_policy_overrides_lower_priority_policy(self) -> None:
        """Verify pull policy flag with higher priority overrides the default pull
        policy --missing"""

        compose_file = compose_yaml_path("override_missing")
        image = "docker.io/library/alpine:latest"

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "up",
                "-d",
            ])

            # Remove image while container is still up
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "-f",
                image,
            ])

            # up container one more time
            _, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "--verbose",
                "-f",
                compose_file,
                "up",
                "-d",
            ])
            # default pull-policy is --missing, but it has been overridden by policy of
            # higher priority --always
            self.assertIn(b"podman pull --policy always alpine:latest", error)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "-f",
                image,
            ])

    @unittest.skipIf(
        get_podman_version() < version.parse("5.6.0"),
        "The image pull policy feature was only added as of Podman 5.6.0.",
    )
    def test_localhost_image_not_pulled(self) -> None:
        """Verify existing localhost/ images are used locally without pulling"""

        compose_file = compose_yaml_path("non_existent_localhost_image")
        image = "localhost/test-image:1"

        try:
            # pre-create image locally by tagging a minimal base image,
            # this simulates the image already existing locally
            self.run_subprocess_assert_returncode(["podman", "pull", "alpine:latest"])
            self.run_subprocess_assert_returncode(["podman", "tag", "alpine:latest", image])

            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "up",
                "-d",
            ])

            # Remove image while container is still up
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "-f",
                image,
            ])

            # since the compose file has both 'build' and 'image', podman-compose
            # should use the existing image (or rebuild if necessary), but it should
            # never attempt to pull localhost/ images
            _, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "--verbose",
                "-f",
                compose_file,
                "up",
                "-d",
            ])
            self.assertNotIn(b"Trying to pull", error)

            # Confirm container is actually started with localhost/ image
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "ps",
                "-a",
                "--filter",
                f"ancestor={image}",
                "--format",
                "{{.Image}}",
            ])
            self.assertIn(b"localhost/test-image:1", output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
            ])
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "-f",
                image,
            ])

    @unittest.skipIf(
        get_podman_version() < version.parse("5.6.0"),
        "The image pull policy feature was only added as of Podman 5.6.0.",
    )
    def test_localhost_image_built_if_does_not_exist(self) -> None:
        """Verify non-existent localhost/ images are built instead of pulling"""

        compose_file = compose_yaml_path("build_localhost_image")
        image = "localhost/not-exists"

        # check image does not exist
        self.run_subprocess_assert_returncode(
            [
                "podman",
                "image",
                "exists",
                image,
            ],
            1,
        )

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "up",
                "-d",
            ])

            # Remove image while container is still up
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "-f",
                image,
            ])

            # image was not pulled, it was built
            output, _ = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "--verbose",
                "-f",
                compose_file,
                "up",
                "-d",
            ])
            self.assertNotIn(b"Trying to pull", output)

            # After up command, image now exists (was built)
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "images",
                "--filter",
                f"reference={image}",
                "--format",
                "{{.Repository}}:{{.Tag}}",
            ])
            self.assertIn(image.encode(), output)

            # Container uses the locally built image
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "ps",
                "-a",
                "--filter",
                f"ancestor={image}",
                "--format",
                "{{.Image}}",
            ])
            self.assertIn(image.encode(), output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
            ])
            self.run_subprocess_assert_returncode(
                ["podman", "rmi", "-f", image],
            )

    def test_recreate_on_image_changed(self) -> None:
        """Verify that containers are recreated when their image changes.

        Simulates pulling a new version of an image by re-tagging a different
        base image under the same tag. Only the service whose image changed
        should be recreated; the unchanged service should keep its container.
        """
        compose_file = compose_yaml_path("image_change")
        tag = "nopush/podman-compose-test:image-change-app"

        try:
            # create the tagged image from the existing base image
            self.run_subprocess_assert_returncode([
                "podman",
                "tag",
                "nopush/podman-compose-test",
                tag,
            ])

            # start containers
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_file, "up", "-d"],
            )

            original_containers = self.get_existing_containers("image_change")

            # simulate a new image version: re-tag a different image under the same tag
            self.run_subprocess_assert_returncode([
                "podman",
                "tag",
                "nopush/podman-compose-test2",
                tag,
            ])

            # verify the app container exists
            self.assertIn(
                "compose_up_behavior_app_1",
                original_containers,
                "app container should exist after initial up",
            )

            # run up again — should detect the changed image and recreate app
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_file, "up", "-d"],
            )

            new_containers = self.get_existing_containers("image_change")

            # app should be recreated (different container ID)
            self.assertNotEqual(
                original_containers["compose_up_behavior_app_1"]["id"],
                new_containers["compose_up_behavior_app_1"]["id"],
                "app container should be recreated when its image changes",
            )

            # db should NOT be recreated (same container ID)
            self.assertEqual(
                original_containers["compose_up_behavior_db_1"]["id"],
                new_containers["compose_up_behavior_db_1"]["id"],
                "db container should not be recreated when its image did not change",
            )

            # all containers should be running
            self.assertTrue(
                all(c["exited"] is False for c in new_containers.values()),
                "Not all containers are running after up command",
            )

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
            self.run_subprocess_assert_returncode(
                ["podman", "rmi", "-f", tag],
            )

    def test_recreate_on_build_image_changed(self) -> None:
        """Verify that containers are recreated when a locally built image changes.

        Builds an image from a Dockerfile, starts containers, modifies the
        Dockerfile to produce a different image, rebuilds with --build, and
        verifies that the service whose image changed is recreated while the
        unchanged service keeps its container.
        """
        compose_file = compose_yaml_path("build_image_change")
        tag = "nopush/podman-compose-test:build-image-change"
        dockerfile = os.path.join(
            os.path.join(test_path(), "compose_up_behavior"),
            "Dockerfile.image_change",
        )

        try:
            # create the Dockerfile for the initial build
            with open(dockerfile, "w") as f:
                f.write("FROM nopush/podman-compose-test\n")

            # build and start containers
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_file, "up", "-d", "--build"],
            )

            original_containers = self.get_existing_containers("build_image_change")

            self.assertIn(
                "compose_up_behavior_app_1",
                original_containers,
                "app container should exist after initial up",
            )

            # modify the Dockerfile to produce a different image
            with open(dockerfile, "w") as f:
                f.write("FROM nopush/podman-compose-test\nRUN touch /marker\n")

            # rebuild and restart — should detect the changed image and recreate app
            self.run_subprocess_assert_returncode(
                [podman_compose_path(), "-f", compose_file, "up", "-d", "--build"],
            )

            new_containers = self.get_existing_containers("build_image_change")

            # app should be recreated (different container ID)
            self.assertNotEqual(
                original_containers["compose_up_behavior_app_1"]["id"],
                new_containers["compose_up_behavior_app_1"]["id"],
                "app container should be recreated when its built image changes",
            )

            # db should NOT be recreated (same container ID)
            self.assertEqual(
                original_containers["compose_up_behavior_db_1"]["id"],
                new_containers["compose_up_behavior_db_1"]["id"],
                "db container should not be recreated when its image did not change",
            )

            # all containers should be running
            self.assertTrue(
                all(c["exited"] is False for c in new_containers.values()),
                "Not all containers are running after up command",
            )

        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
            self.run_subprocess_assert_returncode(
                ["podman", "rmi", "-f", tag],
            )
            os.remove(dockerfile)

    def run_pull_policy_up_twice(
        self, scenario: str, image: str, dockerfile_name: str, *extra_up_args: str
    ) -> tuple[str, bytes]:
        """
        Run `up` twice for a build-based service, modifying the Dockerfile in between.
        """
        compose_file = compose_yaml_path(scenario)
        dockerfile = os.path.join(os.path.join(test_path(), "compose_up_behavior"), dockerfile_name)
        self.addCleanup(remove_file_if_exists, dockerfile)
        self.addCleanup(self._cleanup_pull_policy, compose_file, image)

        # create the Dockerfile for the initial build
        with open(dockerfile, "w") as f:
            f.write("FROM alpine:latest\n")

        # first up builds the image
        self.run_subprocess_assert_returncode(
            [podman_compose_path(), "-f", compose_file, "up", "-d"],
        )

        # image now exists locally
        self.run_subprocess_assert_returncode(["podman", "image", "exists", image])
        original_image_id = self.get_image_id(image)

        # modify the Dockerfile so a rebuild yields a different image
        with open(dockerfile, "w") as f:
            f.write("FROM alpine:latest\nRUN touch /marker\n")

        # second up, with the caller-provided extra arguments
        _, error = self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "--verbose",
            "-f",
            compose_file,
            "up",
            *extra_up_args,
            "-d",
        ])
        return original_image_id, error

    def _cleanup_pull_policy(self, compose_file: str, image: str) -> None:
        self.run_subprocess_assert_returncode([
            podman_compose_path(),
            "-f",
            compose_file,
            "down",
            "-t",
            "0",
        ])
        if self.run_subprocess(["podman", "image", "exists", image])[2] == 0:
            self.run_subprocess_assert_returncode(["podman", "rmi", "-f", image])

    def test_pull_policy_build_rebuilds_existing_image(self) -> None:
        """
        The Dockerfile is modified between the two `up` invocations so that a
        rebuild produces a different image ID; the second `up` must rebuild and
        therefore replace the local image.
        """
        image = "localhost/pull-policy-build-test"
        original_image_id, error = self.run_pull_policy_up_twice(
            "pull_policy_build", image, "Dockerfile.pull_policy_build"
        )
        self.assertIn(b"podman build", error)
        self.assertNotEqual(
            original_image_id,
            self.get_image_id(image),
        )

    def test_pull_policy_missing_reuses_existing_image(self) -> None:
        """
        The Dockerfile is modified between the two `up` invocations; because the
        service does not request `pull_policy: build`, the existing local image
        must be reused and its ID must stay the same.
        """
        image = "localhost/pull-policy-missing-test"
        original_image_id, error = self.run_pull_policy_up_twice(
            "pull_policy_missing", image, "Dockerfile.pull_policy_missing"
        )
        self.assertNotIn(b"podman build", error)
        self.assertEqual(
            original_image_id,
            self.get_image_id(image),
        )

    def test_cli_pull_never_overrides_pull_policy_build(self) -> None:
        """
        CLI `--pull=never` must suppress the rebuild that `pull_policy: build`
        would otherwise force.
        """
        image = "localhost/pull-policy-build-test"
        original_image_id, error = self.run_pull_policy_up_twice(
            "pull_policy_build", image, "Dockerfile.pull_policy_build", "--pull=never"
        )
        self.assertNotIn(b"podman build", error)
        self.assertEqual(original_image_id, self.get_image_id(image))

    def test_cli_pull_build_forces_rebuild_no_pull_policy_build(self) -> None:
        image = "localhost/pull-policy-missing-test"
        original_image_id, error = self.run_pull_policy_up_twice(
            "pull_policy_missing", image, "Dockerfile.pull_policy_missing", "--pull=build"
        )
        self.assertIn(b"podman build", error)
        self.assertNotEqual(original_image_id, self.get_image_id(image))

    def test_pull_policy_build_without_build_section_does_not_pull(self) -> None:
        compose_file = compose_yaml_path("pull_policy_build_no_build_section")
        image = "docker.io/library/alpine:latest"

        try:
            # make sure the image is absent so the pull decision actually matters
            self.run_subprocess_assert_returncode(["podman", "rmi", "--ignore", "-f", image])
            self.run_subprocess_assert_returncode(["podman", "image", "exists", image], 1)

            # `up` must not pull the image: podman is told --pull=never
            _, error, _ = self.run_subprocess([
                podman_compose_path(),
                "--verbose",
                "-f",
                compose_file,
                "up",
                "-d",
            ])
            self.assertIn(b"--pull=never", error)

            # the image must not have been pulled
            self.run_subprocess_assert_returncode(["podman", "image", "exists", image], 1)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
            self.run_subprocess_assert_returncode(["podman", "rmi", "--ignore", "-f", image])

    def test_cli_pull_always_ignored_for_localhost_image(self) -> None:
        compose_file = compose_yaml_path("build_localhost_image")
        image = "localhost/not-exists"

        try:
            # `--pull=always` must not break a locally built image
            _, error = self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "--verbose",
                "-f",
                compose_file,
                "up",
                "--pull=always",
                "-d",
            ])
            # the CLI pull policy must not be forwarded to `podman create`
            create_line = next(line for line in error.splitlines() if b"podman create" in line)
            self.assertEqual(create_line.count(b"--pull="), 0)

            # the container was created from the local image
            output, _ = self.run_subprocess_assert_returncode([
                "podman",
                "ps",
                "-a",
                "--filter",
                f"ancestor={image}",
                "--format",
                "{{.Image}}",
            ])
            self.assertIn(image.encode(), output)
        finally:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
            self.run_subprocess_assert_returncode(["podman", "rmi", "--ignore", "-f", image])

    def test_run_pull_never_does_not_pull_image(self) -> None:
        """Verify `run --pull=never` forwards the policy to `podman run`.
        With `--pull=never`, podman-compose must pass the policy through to
        `podman run` so that podman fails immediately when the image is not
        available locally, instead of trying to reach a registry.
        """
        compose_file = compose_yaml_path("pull_never_run")
        image = "localhost/does-not-exist:latest"

        # make sure the image does not exist locally
        self.run_subprocess_assert_returncode(
            ["podman", "image", "exists", image],
            expected_returncode=1,
        )

        try:
            # the command is expected to fail because the image is missing,
            # but it must fail without attempting to pull from a registry
            _, error, _ = self.run_subprocess([
                podman_compose_path(),
                "--verbose",
                "-f",
                compose_file,
                "run",
                "--pull=never",
                "test",
                "echo",
                "hi",
            ])

            # the pull policy must be forwarded to podman run
            self.assertIn(b"--pull=never", error)
            # podman must not try to reach a registry
            self.assertNotIn(b"Trying to pull", error)
        finally:
            self.run_subprocess([
                podman_compose_path(),
                "-f",
                compose_file,
                "down",
                "-t",
                "0",
            ])
