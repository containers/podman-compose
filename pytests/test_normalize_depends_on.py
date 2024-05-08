import copy

from podman_compose import normalize_service

test_cases_simple = [
    (
        {"depends_on": "my_service"},
        {"depends_on": {"my_service": {"condition": "service_started"}}},
    ),
    (
        {"depends_on": ["my_service"]},
        {"depends_on": {"my_service": {"condition": "service_started"}}},
    ),
    (
        {"depends_on": ["my_service1", "my_service2"]},
        {
            "depends_on": {
                "my_service1": {"condition": "service_started"},
                "my_service2": {"condition": "service_started"},
            },
        },
    ),
    (
        {"depends_on": {"my_service": {"condition": "service_started"}}},
        {"depends_on": {"my_service": {"condition": "service_started"}}},
    ),
    (
        {"depends_on": {"my_service": {"condition": "service_healthy"}}},
        {"depends_on": {"my_service": {"condition": "service_healthy"}}},
    ),
]


def test_normalize_service_simple():
    for test_case, expected in copy.deepcopy(test_cases_simple):
        test_original = copy.deepcopy(test_case)
        test_case = normalize_service(test_case)
        test_result = expected == test_case
        if not test_result:
            print("test:     ", test_original)
            print("expected: ", expected)
            print("actual:   ", test_case)
        assert test_result
