import pytest

from khmer_engine.lexicon import Lexicon
from khmer_engine.match import Matcher, Weights, forms


@pytest.fixture(scope="module")
def matcher():
    return Matcher(Lexicon.sample(), curated=[("jg", "ចង់")])


def test_words_are_indexed_under_each_romanization():
    by_source = {f.source: f.spelling for f in forms("ខ្មែរ", ["k m ae"])}
    assert by_source == {"pronunciation": "kmae", "spelling": "khmaer", "ungegn": "khmer"}


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
