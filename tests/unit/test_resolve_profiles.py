import unittest

from podman_compose import PodmanCompose


class TestResolveProfiles(unittest.TestCase):
    def setUp(self):
        self.compose = PodmanCompose()

    def test_no_profiles(self):
        defined_services = {
            "web": {"image": "nginx"},
            "db": {"image": "postgres"},
        }
        services = self.compose._resolve_profiles(defined_services, {"test"})
        self.assertIn("web", services)
        self.assertIn("db", services)

    def test_matching_profile(self):
        defined_services = {
            "web": {"image": "nginx", "profiles": ["frontend"]},
            "db": {"image": "postgres", "profiles": ["backend"]},
        }
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertNotIn("db", services)

    def test_depends_on_pulls_dependency(self):
        defined_services = {
            "web": {"image": "nginx", "profiles": ["frontend"], "depends_on": ["db"]},
            "db": {"image": "postgres", "profiles": ["backend"]},
            "cache": {"image": "redis", "profiles": ["backend"]},
        }
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertIn("db", services)
        self.assertNotIn("cache", services)

    def test_depends_on_dict_pulls_dependency(self):
        defined_services = {
            "web": {
                "image": "nginx",
                "profiles": ["frontend"],
                "depends_on": {"db": {"condition": "service_healthy"}},
            },
            "db": {"image": "postgres", "profiles": ["backend"]},
        }
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertIn("db", services)

    def test_extends_pulls_dependency(self):
        defined_services = {
            "web": {"image": "nginx", "profiles": ["frontend"], "extends": "base-web"},
            "base-web": {"image": "nginx:alpine", "profiles": ["backend"]},
        }
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertIn("base-web", services)

    def test_extends_dict_pulls_dependency(self):
        defined_services = {
            "web": {"image": "nginx", "profiles": ["frontend"], "extends": {"service": "base-web"}},
            "base-web": {"image": "nginx:alpine", "profiles": ["backend"]},
        }
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertIn("base-web", services)

    def test_transitive_dependencies(self):
        defined_services = {
            "web": {"image": "nginx", "profiles": ["frontend"], "depends_on": ["api"]},
            "api": {"image": "node", "profiles": ["backend"], "depends_on": ["db"]},
            "db": {"image": "postgres", "profiles": ["database"]},
        }
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertIn("api", services)
        self.assertIn("db", services)

    def test_circular_dependencies(self):
        defined_services = {
            "a": {"image": "alpine", "profiles": ["group1"], "depends_on": ["b"]},
            "b": {"image": "alpine", "profiles": ["group2"], "depends_on": ["a"]},
        }
        services = self.compose._resolve_profiles(defined_services, {"group1"})
        self.assertIn("a", services)
        self.assertIn("b", services)

    def test_missing_dependency(self):
        defined_services = {
            "web": {
                "image": "nginx",
                "profiles": ["frontend"],
                "depends_on": ["non_existent_service"],
            }
        }
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertNotIn("non_existent_service", services)

    def test_invalid_dependency_format(self):
        defined_services = {
            "web": {
                "image": "nginx",
                "profiles": ["frontend"],
                # Invalid format: depends_on should be list or dict
                "depends_on": "db",
                # Invalid format: extends should be str or dict
                "extends": ["db"],
            },
            "db": {"image": "postgres", "profiles": ["backend"]},
        }
        # It should not crash, and should just include 'web' without 'db'
        services = self.compose._resolve_profiles(defined_services, {"frontend"})
        self.assertIn("web", services)
        self.assertNotIn("db", services)
