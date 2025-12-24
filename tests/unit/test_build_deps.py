import unittest

from podman_compose import PodmanCompose


# Test the build-time resolution of dependencies created by the service:service in
# the `build.additional_contexts` section.
class TestResolveContextDependencies(unittest.TestCase):
    def setUp(self):
        self.compose = PodmanCompose()
        # project_name is used in format_name if image is not present
        self.compose.project_name = "test_project"

    def test_resolve_context_dependencies_simple(self):
        services = {
            "service_a": {"image": "image_a"},
            "service_b": {"build": {"additional_contexts": ["img=service:service_a"]}},
        }
        self.compose._resolve_context_dependencies(services)

        build_deps = services["service_b"]["build"].get("build_deps")
        self.assertEqual(build_deps, ["service_a"])

        contexts = services["service_b"]["build"]["additional_contexts"]
        # The dependency uses the specified image name from the service
        self.assertTrue(any("img=docker://image_a" in c for c in contexts))

    def test_resolve_context_dependencies_no_image_in_target(self):
        services = {
            "service_a": {},  # No image
            "service_b": {"build": {"additional_contexts": ["img=service:service_a"]}},
        }
        self.compose._resolve_context_dependencies(services)

        contexts = services["service_b"]["build"]["additional_contexts"]
        # Default name format: localhost/project_service
        expected_image = "docker://localhost/test_project_service_a"
        self.assertTrue(any(expected_image in c for c in contexts))

    def test_circular_dependencies(self):
        services = {"service_a": {"build": {"additional_contexts": ["ctx=service:service_a"]}}}
        with self.assertRaises(ValueError):
            self.compose._resolve_context_dependencies(services)

        services = {
            "service_a": {"build": {"additional_contexts": ["ctx=service:service_b"]}},
            "service_b": {"build": {"additional_contexts": ["ctx=service:service_c"]}},
            "service_c": {"build": {"additional_contexts": ["ctx=service:service_a"]}},
        }
        with self.assertRaises(ValueError):
            self.compose._resolve_context_dependencies(services)

    def test_diamond_dependency_valid(self):
        # A depends on B and C. B depends on D. C depends on D.
        # This is a perfectly cromulent arrangement
        services = {
            "service_a": {
                "build": {
                    "additional_contexts": ["ctx1=service:service_b", "ctx2=service:service_c"]
                }
            },
            "service_b": {"build": {"additional_contexts": ["ctx=service:service_d"]}},
            "service_c": {"build": {"additional_contexts": ["ctx=service:service_d"]}},
            "service_d": {"image": "image_d"},
        }
        self.compose._resolve_context_dependencies(services)

        self.assertEqual(["service_b", "service_c"], services["service_a"]["build"]["build_deps"])
        self.assertEqual(["service_d"], services["service_b"]["build"]["build_deps"])
        self.assertEqual(["service_d"], services["service_c"]["build"]["build_deps"])
