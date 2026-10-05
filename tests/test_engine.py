import pytest

from khmer_engine.engine import Engine


@pytest.fixture(scope="module")
def engine():
    return Engine()


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("sok sabay te", "សុខសប្បាយទេ"),
        ("orkun", "អរគុណ"),
        ("Orkun Bong", "អរគុណបង"),  # case does not matter
        ("or kun", "អរគុណ"),  # one word typed as two
        ("ot mean te", "អត់មានទេ"),
        ("nham bay hoy nov", "ញ៉ាំបាយហើយនៅ"),
    ],
)
def test_convert(engine, typed, expected):
    assert engine.convert(typed) == expected


def test_punctuation_line_breaks_and_khmer_script_pass_through(engine):
    assert engine.convert("sok sabay te?\norkun!") == "សុខសប្បាយទេ?\nអរគុណ!"
    assert engine.convert("ខ្ញុំ ot te") == "ខ្ញុំ អត់ទេ"


def test_empty_input(engine):
    assert engine.convert("") == ""
    assert engine.analyze("").tokens == []


def test_sok_sabay_is_suggested_as_one_word(engine):
    # The spec's own example: "sok sabay" gives សុខសប្បាយ.
    (token, _) = engine.analyze("sok sabay te").tokens
    assert (token.typed, token.choices[0].text) == ("sok sabay", "សុខសប្បាយ")


def test_alternatives_start_with_the_best_conversion(engine):
    result = engine.analyze("sok sabay te", n=3)
    assert result.alternatives[0] == result.text
    assert 1 < len(result.alternatives) <= 3
    assert len(set(result.alternatives)) == len(result.alternatives)


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("ot mean wifi te", "អត់មាន wifi ទេ"),
        ("ok bong", "ok បង"),
        ("send photo mok", "send photo មក"),
        ("iPhone thmey", "iPhone ថ្មី"),  # the typed case is kept
    ],
)
def test_english_words_stay_in_latin_letters(engine, typed, expected):
    assert engine.convert(typed) == expected


def test_words_on_the_english_list_can_still_be_khmer():
    # Keeping a word in English has a cost, so a good Khmer reading in context wins.
    assert Engine(english=frozenset({"te"})).convert("ot mean te") == "អត់មានទេ"
