import pytest

from khmer_engine import script


def test_every_consonant_has_exactly_one_series():
    assert len(script.CONSONANTS) == 35
    assert not script.A_SERIES & script.O_SERIES


@pytest.mark.parametrize(
    ("consonant", "expected"),
    [("ក", "a"), ("គ", "o"), ("ណ", "a"), ("ន", "o"), ("ប", "a"), ("ព", "o"), ("អ", "a")],
)
def test_series(consonant, expected):
    assert script.series(consonant) == expected


def test_series_rejects_non_consonants():
    with pytest.raises(ValueError, match="not a Khmer consonant"):
        script.series("ា")


@pytest.mark.parametrize("ch", ["ក", "ា", "\u17d2", "ំ", "៉", "ឥ", "\u200c"])
def test_khmer_letters(ch):
    assert script.is_khmer_letter(ch)


@pytest.mark.parametrize("ch", ["a", " ", "។", "១", "?"])
def test_not_khmer_letters(ch):
    assert not script.is_khmer_letter(ch)
