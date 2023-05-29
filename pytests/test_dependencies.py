import pytest

from podman_compose import flat_deps, DependsCondition


@pytest.fixture
def basic_services():
    return {
        "foo": {},
        "bar": {
            # string dependency
            "depends_on": "foo",
        },
        "baz": {
            # list dependency
            "depends_on": ["bar"],
        },
        "ham": {
            # dict / conditional dependency
            "depends_on": {
                "foo": {
                    "condition": "service_healthy",
                },
            },
        },
    }


def test_flat_deps(basic_services):
    flat_deps(basic_services)
    assert basic_services["foo"]["_deps"] == {}
    assert basic_services["bar"]["_deps"] == {"foo": DependsCondition.STARTED}
    assert basic_services["baz"]["_deps"] == {
        "bar": DependsCondition.STARTED,
        "foo": DependsCondition.STARTED,
    }
    assert basic_services["ham"]["_deps"] == {"foo": DependsCondition.HEALTHY}
