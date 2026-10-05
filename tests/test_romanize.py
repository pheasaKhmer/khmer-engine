import pytest

from khmer_engine.engine import Engine
from khmer_engine.romanize import _aspirate, merge_unknown
from khmer_engine.segment import Word


@pytest.fixture(scope="module")
def engine():
    return Engine()


@pytest.mark.parametrize(
    ("khmer", "chat", "ungegn"),
    [
        ("សួស្តី! សុខសប្បាយទេ?", "suosdey! soksabay te?", "suŏsdei! sŏkhsâbbay té?"),
        ("ខ្ញុំស្រឡាញ់អូន។", "khnhom srolanh oun.", "khnhom srâlănh on."),
        ("ភ្នំពេញ​កម្ពុជា", "phnumpenh kampuchea", "phnumpénh kâmpŭchéa"),
    ],
)
def test_styles(engine, khmer, chat, ungegn):
    assert engine.romanize(khmer) == chat
    assert engine.romanize(khmer, "ungegn") == ungegn


def test_coeng_da_and_coeng_ta_give_the_same_result(engine):
    assert engine.romanize("សួស្ដី") == engine.romanize("សួស្តី")


def test_text_that_is_not_khmer_is_kept(engine):
    assert engine.romanize("ខ្ញុំ love អូន") == "khnhom love oun"
    assert engine.romanize("hello") == "hello"
    assert engine.romanize("") == ""


def test_digits_become_ascii_and_stay_apart_from_words(engine):
    assert engine.romanize("ឆ្នាំ២០២៦") == "chhnam 2026"
    assert engine.romanize("២០២៦ឆ្នាំ") == "2026 chhnam"


def test_repeat_sign_repeats_the_word(engine):
    assert engine.romanize("ផ្សេងៗ") == "phseng phseng"


def test_unknown_words_are_romanized_from_their_spelling(engine):
    # Not in the sample lexicon, so the chat rules spell them.
    assert engine.romanize("ហ្ឫទ័យ") == "hruetey"
    assert engine.romanize("ចក្រពត្តិ") == "chakropotde"


def test_unknown_pieces_absorb_the_bare_letters_around_them():
    words = [Word("ច", True), Word("ក្រ", True), Word("ត្តិ", False), Word("ទេ", True)]
    assert merge_unknown(words) == [Word("ចក្រត្តិ", False), Word("ទេ", True)]


def test_bare_letters_alone_stay_words():
    words = [Word("ក", True), Word("ខ", True)]
    assert merge_unknown(words) == words


@pytest.mark.parametrize(
    ("spoken", "written", "expected"),
    [
        ("pnum", "phnum", "phnum"),
        ("knhom", "khnhom", "khnhom"),
        ("chnam", "chhnam", "chhnam"),
        ("phteah", "phteah", "phteah"),  # already aspirated
        ("mean", "mean", "mean"),
        ("kampuchea", "kampuchea", "kampuchea"),  # k is not aspirated in the spelling
    ],
)
def test_aspiration_comes_from_the_spelling(spoken, written, expected):
    assert _aspirate(spoken, written) == expected
