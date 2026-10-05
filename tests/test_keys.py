import pytest

from khmer_engine.keys import consonants, fold, key, without_first_vowel


def test_fold_keeps_lowercase_ascii_letters():
    assert fold("Kâmpŭchéa") == "kampuchea"
    assert fold("l'â 2 Stœng") == "lastoeng"


@pytest.mark.parametrize(
    "spellings",
    [
        # The variants the spec lists: ou/o/u, ae/e, k/g, ch/j, doubles, trailing h.
        ["touch", "toch", "tuch"],
        ["khmer", "khmae", "kmer", "khmaer"],
        ["kom", "gom"],
        ["chong", "jong"],
        ["sabbay", "sabay"],
        ["preah", "prea"],
        # Others that are common in chat.
        ["sous dey", "suosdey", "sousdey", "sursdey", "suos'dei"],
        ["orkun", "okun", "or kun", "orkoun"],
        ["sabay", "sabai"],
        ["pros", "proh"],
        ["mean", "mian", "mien"],
        ["nham", "nyam"],
        ["srey", "srei"],
        ["teuk", "toek", "tuek", "tek"],
        ["kaoh", "koh"],
        ["min", "men"],
        ["tov", "tow"],
        # UNGEGN spellings match chat spellings.
        ["kampuchea", "Kâmpŭchéa"],
    ],
)
def test_variants_share_a_key(spellings):
    assert len({key(s) for s in spellings}) == 1, {s: key(s) for s in spellings}


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("bong", "bang"),  # different vowels stay apart
        ("bong", "pong"),  # b and p stay apart
        ("te", "tea"),
    ],
)
def test_different_words_keep_different_keys(first, second):
    assert key(first) != key(second)


def test_r_before_a_vowel_is_kept():
    assert key("srolanh") == "srOlAY"
    assert key("kara") == "kArA"


def test_empty():
    assert key("") == ""
    assert key("123 ?!") == ""


def test_text_that_continues_keeps_its_last_r_h_and_s():
    assert key("dar") == "dA"
    assert key("dar", final=False) == "dAr"
    assert key("preah", final=False) == "prJh"


@pytest.mark.parametrize(
    ("spelling", "expected"),
    [("tov", "tv"), ("deng", "dg"), ("chong", "chg"), ("kheng", "khg"), ("te", None), ("", None)],
)
def test_consonants_abbreviate_a_spelling(spelling, expected):
    assert consonants(spelling) == expected


@pytest.mark.parametrize(
    ("spelling", "nasal", "expected"),
    [
        ("sabay", False, "sbay"),
        ("rovol", False, "rvol"),
        ("tomne", True, "tne"),
        ("tomne", False, None),  # a closed first syllable keeps its vowel
        ("somtos", False, None),
        ("orkun", False, None),  # no consonant before the vowel
        ("tov", False, None),  # one syllable
    ],
)
def test_without_first_vowel(spelling, nasal, expected):
    assert without_first_vowel(spelling, nasal) == expected
