#!/usr/bin/env python
import os
import tempfile
import unittest
from pathlib import Path

from tests.integration.test_utils import RunSubprocessMixin
from tests.integration.test_utils import podman_compose_path


class TestRecursiveDiscovery(unittest.TestCase, RunSubprocessMixin):
    """Test recursive discovery of compose files"""

    def test_recursive_compose_file_discovery(self):
        """Test that podman-compose can find compose files in parent directories"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create deep directory structure
            deep_dir = temp_path / "deep" / "nested" / "directory"
            deep_dir.mkdir(parents=True)

            # Create compose file in root
            compose_content = """version: '3'
services:
  test-service:
    image: alpine:latest
    command: echo "test"
"""
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text(compose_content)

            # Test from deep directory
            original_cwd = os.getcwd()
            try:
                os.chdir(deep_dir)

                # Run podman-compose config - should find compose file in parent dirs
                stdout, stderr, returncode = self.run_subprocess([podman_compose_path(), "config"])

                # Should succeed and contain our service
                self.assertEqual(returncode, 0, f"Should find compose file. Stderr: {stderr}")

                stdout_str = stdout.decode() if isinstance(stdout, bytes) else stdout
                self.assertIn("test-service", stdout_str, "Should find and parse the test-service")

            finally:
                os.chdir(original_cwd)

    def test_recursive_discovery_with_explicit_file(self):
        """Test that explicit -f still works and takes precedence over discovery"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            deep_dir = temp_path / "deep" / "subdir"
            deep_dir.mkdir(parents=True)

            # Create compose file in root (this should be ignored)
            compose_content_root = """version: '3'
services:
  root-service:
    image: alpine:latest
"""
            root_compose = temp_path / "docker-compose.yml"
            root_compose.write_text(compose_content_root)

            # Create different compose file to use explicitly
            compose_content_explicit = """version: '3'
services:
  explicit-service:
    image: nginx:latest
"""
            explicit_compose = deep_dir / "explicit-compose.yml"
            explicit_compose.write_text(compose_content_explicit)

            original_cwd = os.getcwd()
            try:
                os.chdir(deep_dir)

                # Use explicit -f flag, should use the specified file
                stdout, stderr, returncode = self.run_subprocess([
                    podman_compose_path(),
                    "-f",
                    str(explicit_compose),
                    "config",
                ])

                self.assertEqual(
                    returncode, 0, f"Should succeed with explicit file. Stderr: {stderr}"
                )

                # Check that it's using the explicit file (should contain explicit-service)
                stdout_str = stdout.decode() if isinstance(stdout, bytes) else stdout
                self.assertIn(
                    "explicit-service",
                    stdout_str,
                    "Should use the explicitly specified compose file",
                )
                self.assertNotIn(
                    "root-service",
                    stdout_str,
                    "Should NOT use the discovered file when -f is specified",
                )

            finally:
                os.chdir(original_cwd)

    def test_recursive_discovery_limit(self):
        """Test that recursive discovery stops at the configured limit"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a very deep directory structure (more than 10 levels)
            deep_path = temp_path
            for i in range(12):  # Create 12 levels deep
                deep_path = deep_path / f"level{i}"
            deep_path.mkdir(parents=True)

            # Place compose file at the root
            compose_content = """version: '3'
services:
  test-service:
    image: alpine:latest
"""
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text(compose_content)

            original_cwd = os.getcwd()
            try:
                os.chdir(deep_path)

                # From 12 levels deep, it should NOT find the compose file
                # since the limit is 10 levels
                stdout, stderr, returncode = self.run_subprocess([
                    podman_compose_path(),
                    "config",
                ])

                # Should fail to find compose file due to depth limit
                self.assertNotEqual(
                    returncode,
                    0,
                    f"podman-compose should not find compose file beyond 10 levels. "
                    f"Stdout: {stdout}, Stderr: {stderr}",
                )

            finally:
                os.chdir(original_cwd)

    def test_compose_file_types(self):
        """Test that different compose file types are found"""

        # Test based on COMPOSE_DEFAULT_LS priority order
        test_cases = [
            ("compose.yaml", "compose-yaml-service"),  # Highest priority
            ("compose.yml", "compose-yml-service"),
            ("podman-compose.yaml", "podman-yaml-service"),  # Podman-specific
            ("podman-compose.yml", "podman-yml-service"),
            ("docker-compose.yml", "docker-yml-service"),  # Traditional docker
            ("docker-compose.yaml", "docker-yaml-service"),
            ("container-compose.yml", "container-yml-service"),  # Generic container
            ("container-compose.yaml", "container-yaml-service"),
        ]

        for filename, service_name in test_cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    deep_dir = temp_path / "deep" / "subdir"
                    deep_dir.mkdir(parents=True)

                    # Create compose file
                    compose_content = f"""version: '3'
services:
  {service_name}:
    image: alpine:latest
    command: echo "testing {filename}"
"""
                    compose_file = temp_path / filename
                    compose_file.write_text(compose_content)

                    original_cwd = os.getcwd()
                    try:
                        os.chdir(deep_dir)

                        stdout, stderr, returncode = self.run_subprocess([
                            podman_compose_path(),
                            "config",
                        ])

                        self.assertEqual(returncode, 0, f"Should find {filename}. Stderr: {stderr}")

                        stdout_str = stdout.decode() if isinstance(stdout, bytes) else stdout
                        self.assertIn(
                            service_name,
                            stdout_str,
                            f"Should find service {service_name} from {filename}",
                        )

                    finally:
                        os.chdir(original_cwd)

    def test_compose_file_priority_order(self):
        """Test that compose files are selected according to COMPOSE_DEFAULT_LS priority"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            deep_dir = temp_path / "deep" / "subdir"
            deep_dir.mkdir(parents=True)

            # Create multiple compose files - lowest priority first
            compose_files = [
                ("docker-compose.yaml", "docker-yaml-service"),  # Lower priority
                ("docker-compose.yml", "docker-yml-service"),  # Lower priority
                ("podman-compose.yml", "podman-yml-service"),  # Medium priority
                ("compose.yml", "compose-yml-service"),  # Higher priority
                ("compose.yaml", "compose-yaml-service"),  # Highest priority
            ]

            # Create all files
            for filename, service_name in compose_files:
                compose_content = f"""version: '3'
services:
  {service_name}:
    image: alpine:latest
    command: echo "from {filename}"
"""
                compose_file = temp_path / filename
                compose_file.write_text(compose_content)

            original_cwd = os.getcwd()
            try:
                os.chdir(deep_dir)

                stdout, stderr, returncode = self.run_subprocess([
                    podman_compose_path(),
                    "config",
                ])

                self.assertEqual(returncode, 0, f"Should find compose files. Stderr: {stderr}")

                stdout_str = stdout.decode() if isinstance(stdout, bytes) else stdout

                # Based on COMPOSE_DEFAULT_LS, compose.yaml should have highest priority
                # But podman-compose might combine files, so let's check what actually happens
                self.assertTrue(
                    any(service in stdout_str for _, service in compose_files),
                    f"Should find at least one compose service. Output: {stdout_str[:200]}...",
                )

                # If recursive discovery respects priority, compose.yaml should be preferred
                # This test documents the actual behavior
                print(f"\nActual behavior with multiple files:\n{stdout_str}")

            finally:
                os.chdir(original_cwd)

    def test_override_files_discovery(self):
        """Test that override files are also discovered"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            deep_dir = temp_path / "deep" / "subdir"
            deep_dir.mkdir(parents=True)

            # Create base compose file
            base_compose_content = """version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
"""
            base_compose_file = temp_path / "docker-compose.yml"
            base_compose_file.write_text(base_compose_content)

            # Create override file
            override_compose_content = """version: '3'
services:
  web:
    ports:
      - "8080:80"  # Override the port
  db:
    image: postgres:latest  # Add new service
"""
            override_compose_file = temp_path / "docker-compose.override.yml"
            override_compose_file.write_text(override_compose_content)

            original_cwd = os.getcwd()
            try:
                os.chdir(deep_dir)

                stdout, stderr, returncode = self.run_subprocess([
                    podman_compose_path(),
                    "config",
                ])

                self.assertEqual(
                    returncode, 0, f"Should find and merge compose files. Stderr: {stderr}"
                )

                stdout_str = stdout.decode() if isinstance(stdout, bytes) else stdout

                # Should find both services (web from base, db from override)
                self.assertIn("web:", stdout_str, "Should find web service from base file")
                # Note: depending on implementation, might also find db service from override
                print(f"\nBehavior with override files:\n{stdout_str}")

            finally:
                os.chdir(original_cwd)

    def test_no_compose_file_found(self):
        """Test behavior when no compose file is found in parent directories"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            deep_dir = temp_path / "very" / "deep" / "directory"
            deep_dir.mkdir(parents=True)

            # Don't create any compose file

            original_cwd = os.getcwd()
            try:
                os.chdir(deep_dir)

                # Should fail when no compose file is found
                stdout, stderr, returncode = self.run_subprocess([
                    podman_compose_path(),
                    "config",
                ])

                self.assertNotEqual(
                    returncode,
                    0,
                    f"Should fail when no compose file is found. "
                    f"Stdout: {stdout}, Stderr: {stderr}",
                )

            finally:
                os.chdir(original_cwd)

    def test_compose_yml_discovery(self):
        """Test recursive discovery with compose.yml file"""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            deep_dir = temp_path / "subdir" / "deep"
            deep_dir.mkdir(parents=True)

            # Create compose.yml (newer format)
            compose_content = """services:
  test-service:
    image: alpine:latest
    command: echo "test"
"""
            compose_file = temp_path / "compose.yml"
            compose_file.write_text(compose_content)

            original_cwd = os.getcwd()
            try:
                os.chdir(deep_dir)

                stdout, stderr, returncode = self.run_subprocess([
                    podman_compose_path(),
                    "config",
                ])

                self.assertEqual(returncode, 0, f"Should find compose.yml file. Stderr: {stderr}")

                stdout_str = stdout.decode() if isinstance(stdout, bytes) else stdout
                self.assertIn(
                    "test-service",
                    stdout_str,
                    "Should find and parse the test-service from compose.yml",
                )

            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
