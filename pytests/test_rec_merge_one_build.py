import copy

import pytest

from podman_compose import rec_merge_one

test_cases = [
    ({}, {"build": "."}, {"build": {"context": "."}}),
    ({"build": "."}, {}, {"build": {"context": "."}}),
    ({"build": "./dir-1"}, {"build": "./dir-2"}, {"build": {"context": "./dir-2"}}),
    ({}, {"build": {"context": "./dir-1"}}, {"build": {"context": "./dir-1"}}),
    ({"build": {"context": "./dir-1"}}, {}, {"build": {"context": "./dir-1"}}),
    (
        {"build": {"context": "./dir-1"}},
        {"build": {"context": "./dir-2"}},
        {"build": {"context": "./dir-2"}},
    ),
    (
        {},
        {"build": {"dockerfile": "./compose.yaml"}},
        {"build": {"dockerfile": "./compose.yaml"}},
    ),
    (
        {"build": {"dockerfile": "./compose.yaml"}},
        {},
        {"build": {"dockerfile": "./compose.yaml"}},
    ),
    (
        {"build": {"dockerfile": "./compose-1.yaml"}},
        {"build": {"dockerfile": "./compose-2.yaml"}},
        {"build": {"dockerfile": "./compose-2.yaml"}},
    ),
    (
        {"build": {"dockerfile": "./compose-1.yaml"}},
        {"build": {"context": "./dir-2"}},
        {"build": {"dockerfile": "./compose-1.yaml", "context": "./dir-2"}},
    ),
    (
        {"build": {"dockerfile": "./compose-1.yaml", "context": "./dir-1"}},
        {"build": {"dockerfile": "./compose-2.yaml", "context": "./dir-2"}},
        {"build": {"dockerfile": "./compose-2.yaml", "context": "./dir-2"}},
    ),
    (
        {"build": {"dockerfile": "./compose-1.yaml"}},
        {"build": {"dockerfile": "./compose-2.yaml", "args": ["ENV1=1"]}},
        {"build": {"dockerfile": "./compose-2.yaml", "args": ["ENV1=1"]}},
    ),
    (
        {"build": {"dockerfile": "./compose-2.yaml", "args": ["ENV1=1"]}},
        {"build": {"dockerfile": "./compose-1.yaml"}},
        {"build": {"dockerfile": "./compose-1.yaml", "args": ["ENV1=1"]}},
    ),
    (
        {"build": {"dockerfile": "./compose-2.yaml", "args": ["ENV1=1"]}},
        {"build": {"dockerfile": "./compose-1.yaml", "args": ["ENV2=2"]}},
        {"build": {"dockerfile": "./compose-1.yaml", "args": ["ENV1=1", "ENV2=2"]}},
    ),
]


def test_rec_merge_one_for_build():
    for base, override, expected in copy.deepcopy(test_cases):
        base_original = copy.deepcopy(base)
        base = rec_merge_one(base, override)
        test_result = expected == base
        if not test_result:
            print("base:     ", base_original)
            print("override: ", override)
            print("expected: ", expected)
            print("actual:   ", base)
        assert test_result


test_cases_with_exceptions = [
    ({}, {"build": 1234}, ValueError),
    ({"build": 1234}, {}, ValueError),
    ({"build": 1234}, {"build": 1234}, ValueError),
    ({"build": []}, {}, ValueError),
    ({}, {"build": []}, ValueError),
    ({"build": []}, {"build": []}, ValueError),
]


def test_rec_merge_one_for_build_eception():
    for base, override, expected_exception in copy.deepcopy(test_cases_with_exceptions):
        base_original = copy.deepcopy(base)
        with pytest.raises(expected_exception):
            base = rec_merge_one(base, override)
            print("base:     ", base_original)
            print("override: ", override)
            print("expected: ", expected_exception)
