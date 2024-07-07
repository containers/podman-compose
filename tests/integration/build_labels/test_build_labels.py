# SPDX-License-Identifier: GPL-2.0


import json
import os
import unittest

from tests.integration.test_podman_compose import podman_compose_path
from tests.integration.test_podman_compose import test_path
from tests.integration.test_utils import RunSubprocessMixin


class TestBuildLabels(unittest.TestCase, RunSubprocessMixin):
    def test_build_labels(self):
        """The build context can contain labels which should be added to the resulting image. They
        can be either an array or a map.
        """

        compose_path = os.path.join(test_path(), "build_labels/docker-compose.yml")

        try:
            self.run_subprocess_assert_returncode([
                podman_compose_path(),
                "-f",
                compose_path,
                "build",
                "test_build_labels_map",
                "test_build_labels_array",
            ])

            expected_labels = {
                "com.example.department": "Finance",
                "com.example.description": "Accounting webapp",
                "com.example.label-with-empty-value": "",
            }

            out, _ = self.run_subprocess_assert_returncode([
                "podman",
                "inspect",
                "my-busybox-build-labels-map",
                "my-busybox-build-labels-array",
            ])

            images = json.loads(out)
            self.assertEqual(len(images), 2)
            labels_map = images[0].get("Config", {}).get("Labels", {})
            labels_array = images[1].get("Config", {}).get("Labels", {})
            for k, v in expected_labels.items():
                self.assertIn(k, labels_map)
                self.assertEqual(labels_map[k], v)
                self.assertIn(k, labels_array)
                self.assertEqual(labels_array[k], v)

        finally:
            self.run_subprocess_assert_returncode([
                "podman",
                "rmi",
                "my-busybox-build-labels-map",
                "my-busybox-build-labels-array",
            ])
