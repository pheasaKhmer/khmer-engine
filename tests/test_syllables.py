import pytest

from khmer_engine.syllables import clusters, syllables


def test_clusters_split_on_base_letters():
    parts = clusters("ក្រុមហ៊ុន")
    assert [c.text for c in parts] == ["ក្រុ", "ម", "ហ៊ុ", "ន"]
    first = parts[0]
    assert (first.base, first.subscripts, first.vowel) == ("ក", ("រ",), "ុ")
    assert parts[2].shifter == "៊"


def test_clusters_skip_text_outside_words():
    assert [c.text for c in clusters("ក a ខ")] == ["ក", "ខ"]


def test_vowel_without_base_gets_its_own_cluster():
    (only,) = clusters("ា")
    assert (only.base, only.vowel) == ("", "ា")


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        # A bare consonant closes the syllable before it.
        ("កក", ["កក"]),
        ("ធនាគារ", ["ធ", "នា", "គារ"]),
        ("អរគុណ", ["អរ", "គុណ"]),
        # The base of a cluster with a subscript closes the syllable before it.
        ("កម្ពុជា", ["កម", "្ពុ", "ជា"]),
        ("កន្ត្រាប់", ["កន", "្ត្រាប់"]),
        ("ចង្អៀត", ["ចង", "្អៀត"]),
        ("អក្សរខ្មែរ", ["អក", "្សរ", "ខ្មែរ"]),
        # A doubled consonant is split across syllables.
        ("សប្បាយ", ["សប", "្បាយ"]),
        ("ទស្សនា", ["ទស", "្ស", "នា"]),
        # Word-final clusters with subscripts are finals.
        ("អង្គ", ["អង្គ"]),
        ("បុណ្យ", ["បុណ្យ"]),
        ("ភ័ព្វ", ["ភ័ព្វ"]),
        # The word does not end on a bare consonant with an inherent vowel.
        ("បេក្ខជន", ["បេក", "្ខ", "ជន"]),
        # Nikahit closes a syllable, except that ាំ still takes ង.
        ("ដំបង", ["ដំ", "បង"]),
        ("ទាំង", ["ទាំង"]),
        # Initial clusters start a syllable.
        ("ក្រចេះ", ["ក្រ", "ចេះ"]),
        ("ស្ត្រី", ["ស្ត្រី"]),
        ("ស្ទឹងត្រែង", ["ស្ទឹង", "ត្រែង"]),
        # Independent vowels.
        ("ឪពុក", ["ឪ", "ពុក"]),
        ("ឥឡូវ", ["ឥ", "ឡូវ"]),
    ],
)
def test_syllable_boundaries(word, expected):
    assert [s.text for s in syllables(word)] == expected


def test_input_is_normalized_first():
    # Coeng da is folded to coeng ta (pheasa rule 3.8).
    assert [s.text for s in syllables("កណ្ដាល")] == ["កណ", "្តាល"]


def test_split_onset_comes_from_the_subscript():
    kam, pu, _ = syllables("កម្ពុជា")
    assert kam.finals == ("ម",)
    assert (pu.onset, pu.subscript_onset, pu.vowel) == (("ព",), True, "ុ")


def test_bantoc_is_recorded_on_the_syllable_it_closes():
    (chak,) = syllables("ចាក់")
    assert chak.bantoc
    assert chak.finals == ("ក",)


def test_robat_on_a_final_marks_its_syllable():
    (thorm,) = syllables("ធម៌")
    assert thorm.robat
    assert thorm.finals == ("ម",)


def test_toandakhiat_marks_a_silent_syllable():
    pou, thi, sat = syllables("ពោធិ៍សាត់")
    assert not pou.silent
    assert thi.silent
    assert not sat.silent


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("ក", "a"),
        ("គ", "o"),
        ("ខ្ពង", "o"),  # a non-sonorant subscript decides
        ("ល្អ", "a"),
        ("ស្វាយ", "a"),  # វ is series-neutral, so the base decides
        ("ខ្ញុំ", "a"),
        ("ហ៊ាង", "o"),  # triisap
        ("ញ៉ាំ", "a"),  # muusikatoan
        ("ឯក", "a"),
    ],
)
def test_series(word, expected):
    assert syllables(word)[0].series == expected


def test_empty_word():
    assert syllables("") == []
