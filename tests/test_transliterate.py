from collections import Counter

from khmer_engine.lexicon import Entry, Lexicon
from khmer_engine.transliterate import Transliterator


def test_table_pairs_spoken_and_written_syllables():
    lexicon = Lexicon(
        {
            "សុភា": Entry("សុភា", 10, ("s o . ph ie",)),
            "តារា": Entry("តារា", 5, ("t aa . r aa",)),
            "កម្ពុជា": Entry("កម្ពុជា", 50, ("k a m . p u ʔ . c ie",)),
        }
    )
    t = Transliterator.from_lexicon(lexicon)
    # A subscript onset is written in full: ្ពុ becomes ពុ.
    assert {t.spelling[k] for k in ("sO", "pJ", "kAm", "pO", "cJ")} == {
        "សុ",
        "ភា",
        "កម",
        "ពុ",
        "ជា",
    }
    assert t.transliterate("sophea") == "សុភា"
    assert t.transliterate("tara") == "តារា"


def test_words_whose_syllables_do_not_line_up_are_skipped():
    # Two written syllables, one spoken: nothing is learned from it.
    lexicon = Lexicon({"ពោធិ៍": Entry("ពោធិ៍", 1, ("p ou",))})
    assert Transliterator.from_lexicon(lexicon).spelling == {}


def make(table: dict[str, dict[str, int]]) -> Transliterator:
    return Transliterator({k: Counter(v) for k, v in table.items()})


def test_most_common_spelling_of_each_syllable_is_used():
    t = make({"dA": {"ដា": 3, "តា": 1}, "rA": {"រ៉ា": 2}})
    assert t.transliterate("dara") == "ដារ៉ា"


def test_syllables_inside_a_word_do_not_start_with_a_vowel():
    # "dar" + "a" covers it just as well, but da-ra is preferred.
    t = make({"dA": {"ដា": 1}, "dAr": {"ដារ": 1}, "A": {"អា": 1}, "rA": {"រា": 1}})
    assert t.transliterate("dara") == "ដារា"


def test_uncovered_text_gives_nothing():
    t = make({"dA": {"ដា": 1}})
    assert t.transliterate("dak") is None
    assert t.transliterate("") is None
    assert t.transliterate("123") is None
