import pytest
from pheasa import normalize

from khmer_engine.lexicon import Lexicon
from khmer_engine.match import (
    Matcher,
    Weights,
    forms,
    read_chat_spellings,
    read_preferred_spellings,
)


@pytest.fixture(scope="module")
def matcher():
    return Matcher(Lexicon.sample(), curated=[("jg", "ចង់")])


def test_words_are_indexed_under_each_romanization():
    by_source = {f.source: f.spelling for f in forms("ខ្មែរ", ["k m ae"])}
    assert by_source == {"pronunciation": "kmae", "spelling": "khmaer", "ungegn": "khmer"}


def test_common_words_are_indexed_by_their_consonants_too():
    by_source = {f.source: f.spelling for f in forms("ទៅ", ["t ɨ w"], abbreviated=True)}
    assert by_source["consonants"] == "tv"
    assert "consonants" not in {f.source for f in forms("ទៅ", ["t ɨ w"])}


@pytest.mark.parametrize(("word", "expected"), [("សប្បាយ", "sbay"), ("ទំនេរ", "tne")])
def test_an_unstressed_first_syllable_is_indexed_without_its_vowel(word, expected):
    lexicon = Lexicon.sample()
    found = forms(word, lexicon.entries[word].pronunciations)
    assert expected in {f.spelling for f in found if f.source == "minor"}


def test_a_written_first_vowel_is_kept():
    assert "minor" not in {f.source for f in forms("សាលា", ["s a . l a"])}


def test_duplicate_romanizations_are_indexed_once():
    spellings = [f.spelling for f in forms("ទៅ", ["t ɨ w"])]
    assert len(spellings) == len(set(spellings))


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("orkun", "អរគុណ"),
        ("mean", "មាន"),
        ("nham", "ញ៉ាំ"),
        ("ot", "អត់"),
        ("te", "ទេ"),
        ("soksabay", "សុខសប្បាយ"),  # one word in the lexicon
        ("khmer", "ខ្មែរ"),  # matches the UNGEGN romanization
        ("Kâmpŭchéa", "កម្ពុជា"),  # diacritics are ignored
    ],
)
def test_best_candidate(matcher, typed, expected):
    assert matcher.lookup(typed)[0].text == expected


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("sousdey", "សួស្តី"),
        ("suosdey", "សួស្តី"),
        ("sursdey", "សួស្តី"),
        ("teuk", "ទឹក"),
        ("tek", "ទឹក"),
    ],
)
def test_spelling_variants_find_the_word(matcher, typed, expected):
    assert expected in [c.text for c in matcher.lookup(typed)]


def test_a_misspelled_key_is_found_one_edit_away(matcher):
    # "orkon" has a different key from អរគុណ, but only by one edit.
    best = matcher.lookup("orkon")[0]
    assert best.text == "អរគុណ"
    assert best.score < matcher.lookup("orkun")[0].score


def test_curated_spellings(matcher):
    best = matcher.lookup("jg")[0]
    assert (best.text, best.source) == ("ចង់", "curated")


@pytest.mark.parametrize(("typed", "expected"), [("tv", "ទៅ"), ("nv", "នៅ"), ("dg", "ដឹង")])
def test_consonants_find_a_common_word(matcher, typed, expected):
    best = matcher.lookup(typed)[0]
    assert (best.text, best.source) == (expected, "consonants")


def test_a_left_out_first_vowel_is_found(matcher):
    best = matcher.lookup("sbay")[0]
    assert (best.text, best.source) == ("សប្បាយ", "minor")


def test_typing_the_vowels_too_matches_better(matcher):
    assert matcher.lookup("tov")[0].score > matcher.lookup("tv")[0].score


def test_candidates_are_ranked_and_limited(matcher):
    candidates = matcher.lookup("bong", n=3)
    assert len(candidates) == 3
    assert [c.score for c in candidates] == sorted((c.score for c in candidates), reverse=True)
    assert "បង" in [c.text for c in candidates]


@pytest.mark.parametrize("typed", ["", "123", "xyzq"])
def test_no_candidates(matcher, typed):
    assert matcher.lookup(typed) == []


def test_weights_change_the_ranking():
    lexicon = Lexicon.sample()
    # With frequency weighted heavily, the most common word wins even one edit away.
    heavy = Matcher(lexicon, weights=Weights(key_edit=0.1, spelling=0.1, frequency=5.0))
    light = Matcher(lexicon, weights=Weights(frequency=0.0))
    assert heavy.lookup("rean")[0].text != light.lookup("rean")[0].text


def test_packaged_chat_spellings_point_at_sample_words():
    spellings = read_chat_spellings()
    assert ("jg", "ចង់") in spellings
    lexicon = Lexicon.sample()
    assert all(normalize(word) in lexicon for _, word in spellings)


def test_completions_start_with_what_was_typed(matcher):
    found = matcher.completions("orku")
    assert "អរគុណ" in found
    assert all(score < 0 for score, _ in found.values())


def test_completions_need_two_key_symbols(matcher):
    assert matcher.completions("o") == {}


def test_completions_leave_out_exact_matches(matcher):
    assert "អរគុណ" not in matcher.completions("orkun")


def test_a_variant_spelling_is_not_offered():
    lexicon = Lexicon.sample()
    both = [c.text for c in Matcher(lexicon).lookup("srolanh")]
    assert {"ស្រឡាញ់", "ស្រលាញ់"} <= set(both)
    preferred = Matcher(lexicon, preferred={"ស្រលាញ់": "ស្រឡាញ់"})
    assert "ស្រលាញ់" not in [c.text for c in preferred.lookup("srolanh")]


def test_packaged_preferred_spellings_point_at_sample_words():
    preferred = read_preferred_spellings()
    assert preferred["ស្រលាញ់"] == "ស្រឡាញ់"
    lexicon = Lexicon.sample()
    assert all(word in lexicon for pair in preferred.items() for word in pair)
