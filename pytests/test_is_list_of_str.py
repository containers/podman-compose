from podman_compose import is_list_of_str


def test_is_list_of_str():
    assert is_list_of_str(["foo", "bar"])
    assert not is_list_of_str(["foo", 1])
    assert not is_list_of_str("foo")
    assert not is_list_of_str([])
    assert not is_list_of_str(1)
    assert not is_list_of_str(None)
