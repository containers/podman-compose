import copy

import pytest
from podman_compose import rec_merge_one


test_keys = ["command", "entrypoint"]
test_cases = [
    ({}, {"$$$": "sh"}, {"$$$": ["sh"]}),
    ({"$$$": "sh"}, {}, {"$$$": ["sh"]}),
    ({"$$$": "sh-1"}, {"$$$": "sh-2"}, {"$$$": ["sh-2"]}),
    ({"$$$": ["sh-1"]}, {"$$$": "sh-2"}, {"$$$": ["sh-2"]}),
    ({"$$$": "sh-1"}, {"$$$": ["sh-2"]}, {"$$$": ["sh-2"]}),
    ({"$$$": "sh-1"}, {"$$$": ["sh-2", "sh-3"]}, {"$$$": ["sh-2", "sh-3"]}),
    ({"$$$": ["sh-1"]}, {"$$$": ["sh-2", "sh-3"]}, {"$$$": ["sh-2", "sh-3"]}),
    ({"$$$": ["sh-1", "sh-2"]}, {"$$$": ["sh-3", "sh-4"]}, {"$$$": ["sh-3", "sh-4"]}),
    ({}, {"$$$": ["sh-3", "sh      4"]}, {"$$$": ["sh-3", "sh      4"]}),
    ({"$$$": "sleep infinity"}, {"$$$": "sh"}, {"$$$": ["sh"]}),
    ({"$$$": "sh"}, {"$$$": "sleep infinity"}, {"$$$": ["sleep", "infinity"]}),
    (
        {},
        {"$$$": "bash -c 'sleep infinity'"},
        {"$$$": ["bash", "-c", "sleep infinity"]},
    ),
]
test_cases_with_exceptions = [
    ({}, {"$$$": 1234}, ValueError),
    ({"$$$": 1234}, {}, ValueError),
    ({"$$$": 1234}, {"$$$": 1234}, ValueError),
    ({"$$$": {}}, {}, ValueError),
    ({}, {"$$$": {}}, ValueError),
    ({"$$$": {}}, {"$$$": {}}, ValueError),
    ({"$$$": []}, {}, ValueError),
    ({}, {"$$$": []}, ValueError),
    ({"$$$": []}, {"$$$": []}, ValueError),
]


def template_to_expression(base, override, expected, key):
    base_copy = copy.deepcopy(base)
    override_copy = copy.deepcopy(override)
    expected_copy = copy.deepcopy(expected)

    expected_copy[key] = expected_copy.pop("$$$")
    if "$$$" in base:
        base_copy[key] = base_copy.pop("$$$")
    if "$$$" in override:
        override_copy[key] = override_copy.pop("$$$")
    return base_copy, override_copy, expected_copy


def test_rec_merge_one_for_command_and_entrypoint():
    for base_template, override_template, expected_template in test_cases:
        for key in test_keys:
            base, override, expected = template_to_expression(
                base_template, override_template, expected_template, key
            )

            base = rec_merge_one(base, override)
            test_result = expected == base
            if not test_result:
                print("base_template:     ", base_template)
                print("override_template: ", override_template)
                print("expected:          ", expected)
                print("actual:            ", base)
            assert test_result

    for (
        base_template,
        override_template,
        expected_exception,
    ) in test_cases_with_exceptions:
        for key in test_keys:
            base, override, expected = template_to_expression(
                base_template, override_template, {"$$$": ""}, key
            )

            with pytest.raises(expected_exception):
                base = rec_merge_one(base, override)
                print("base_template:     ", base_template)
                print("override_template: ", override_template)
                print("expected:          ", expected_exception)
