import unittest

from podman_compose import ServiceDependencyCondition


class TestServiceDependencyCondition(unittest.TestCase):
    def test_service_completed_successfully_maps_to_stopped(self) -> None:
        condition = ServiceDependencyCondition.from_value("service_completed_successfully")
        self.assertEqual(condition, ServiceDependencyCondition.STOPPED)

    def test_service_healthy_maps_correctly(self) -> None:
        condition = ServiceDependencyCondition.from_value("service_healthy")
        self.assertEqual(condition, ServiceDependencyCondition.HEALTHY)

    def test_service_started_maps_to_running(self) -> None:
        condition = ServiceDependencyCondition.from_value("service_started")
        self.assertEqual(condition, ServiceDependencyCondition.RUNNING)

    def test_direct_condition_values(self) -> None:
        self.assertEqual(
            ServiceDependencyCondition.from_value("stopped"),
            ServiceDependencyCondition.STOPPED,
        )
        self.assertEqual(
            ServiceDependencyCondition.from_value("healthy"),
            ServiceDependencyCondition.HEALTHY,
        )
        self.assertEqual(
            ServiceDependencyCondition.from_value("running"),
            ServiceDependencyCondition.RUNNING,
        )

    def test_invalid_condition_raises_error(self) -> None:
        with self.assertRaises(ValueError):
            ServiceDependencyCondition.from_value("invalid_condition")
