import pytest

from khmer_engine.keys import fold, key


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
