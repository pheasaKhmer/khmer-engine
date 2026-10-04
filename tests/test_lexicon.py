import math

import pytest

from khmer_engine.lexicon import Lexicon


@pytest.fixture
def lexicon_dir(tmp_path):
    (tmp_path / "lexicon.tsv").write_text(
        "# word\tcount\tpronunciations\n"
        "សុខ\t30\ts o k\n"
        "សប្បាយ\t20\ts a p . ɓ aa j\n"
        "ទេ\t50\tt ee\n"
        "ស្ដី\t5\ts ɗ ə j\n"  # coeng da; normalizes to the next spelling
        "ស្តី\t3\t\n"
        "បាលី\t1\tɓ aa . l ii|ɓ aa . l ə j\n",
        encoding="utf-8",
    )
    (tmp_path / "bigrams.tsv").write_text("សុខ\tសប្បាយ\t10\nសប្បាយ\tទេ\t4\n", encoding="utf-8")
    return tmp_path


def test_load(lexicon_dir):
    lexicon = Lexicon.load(lexicon_dir)
    assert len(lexicon) == 5
    assert lexicon.entries["សុខ"].pronunciations == ("s o k",)
    assert lexicon.entries["បាលី"].pronunciations == ("ɓ aa . l ii", "ɓ aa . l ə j")
    assert lexicon.total == 109


def test_spellings_that_normalize_alike_are_merged(lexicon_dir):
    lexicon = Lexicon.load(lexicon_dir)
    assert "ស្ដី" not in lexicon
    merged = lexicon.entries["ស្តី"]
    assert merged.count == 8
    assert merged.pronunciations == ("s ɗ ə j",)


def test_unigram_probabilities(lexicon_dir):
    lexicon = Lexicon.load(lexicon_dir)
    assert lexicon.logprob("ទេ") > lexicon.logprob("សុខ") > lexicon.logprob("unknown")
    assert math.isfinite(lexicon.logprob("unknown"))


def test_bigram_probabilities(lexicon_dir):
    lexicon = Lexicon.load(lexicon_dir)
    after_sok = lexicon.bigram_logprob("សុខ", "សប្បាយ")
    assert after_sok > lexicon.logprob("សប្បាយ")
    assert lexicon.bigram_logprob("សុខ", "ទេ") < after_sok
    # No bigrams for this word: fall back to the unigram probability.
    assert lexicon.bigram_logprob("ទេ", "សុខ") == pytest.approx(lexicon.logprob("សុខ"))


def test_bigrams_are_optional(tmp_path):
    (tmp_path / "lexicon.tsv").write_text("ទេ\t1\n", encoding="utf-8")
    lexicon = Lexicon.load(tmp_path)
    assert lexicon.bigrams == {}
    assert lexicon.entries["ទេ"].pronunciations == ()


def test_too_many_fields_is_an_error(tmp_path):
    (tmp_path / "lexicon.tsv").write_text("ទេ\t1\tt ee\textra\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"lexicon.tsv:1"):
        Lexicon.load(tmp_path)
