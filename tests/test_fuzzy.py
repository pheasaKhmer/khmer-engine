import pytest

from khmer_engine.fuzzy import distance, neighbours


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("", "", 0),
        ("", "abc", 3),
        ("sok", "sok", 0),
        ("sok", "sork", 1),  # insertion
        ("sabay", "saby", 1),  # deletion
        ("bong", "bang", 1),  # substitution
        ("sabay", "sbaay", 1),  # swap
        ("kitten", "sitting", 3),
    ],
)
def test_distance(a, b, expected):
    assert distance(a, b) == expected
    assert distance(b, a) == expected


def test_neighbours_are_exactly_one_edit_away():
    found = set(neighbours("sok", "abko"))
    assert "sok" not in found
    assert {"sk", "ok", "so", "osk", "sko", "soka", "asok", "sak", "bok"} <= found
    assert all(distance("sok", other) == 1 for other in found)


def test_neighbours_of_the_empty_string_are_single_letters():
    assert set(neighbours("", "ab")) == {"a", "b"}
