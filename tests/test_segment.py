from khmer_engine.segment import KHMER_RUN, Segmenter, Word, cluster_starts


def test_cluster_starts():
    # ក្រុ is one cluster (the រ is a subscript), ម another.
    assert cluster_starts("ក្រុម") == [0, 4, 5]
    assert cluster_starts("") == [0, 0]


def test_khmer_runs_stop_at_spaces_punctuation_and_digits():
    text = "សុខ សប្បាយ។ ១២ ok\u200bទេ"
    assert KHMER_RUN.findall(text) == ["សុខ", "សប្បាយ", "ទេ"]


COSTS = {"សុខ": 2.0, "សប្បាយ": 2.0, "សុខសប្បាយ": 3.0, "ទេ": 1.0, "ក": 1.0}


def test_prefers_the_cheapest_split():
    words = Segmenter(COSTS, unknown_cost=10).segment("សុខសប្បាយទេ")
    assert words == [Word("សុខសប្បាយ", True), Word("ទេ", True)]


def test_costs_decide_between_splits():
    costs = {**COSTS, "សុខសប្បាយ": 5.0}
    words = Segmenter(costs, unknown_cost=10).segment("សុខសប្បាយ")
    assert [w.text for w in words] == ["សុខ", "សប្បាយ"]


def test_unknown_clusters_are_merged_into_one_word():
    words = Segmenter(COSTS, unknown_cost=10).segment("ទេខគឃទេ")
    assert words == [Word("ទេ", True), Word("ខគឃ", False), Word("ទេ", True)]


def test_words_never_end_inside_a_cluster():
    # ក is a word, but in ក្រ it is the base of a cluster, so it cannot match there.
    words = Segmenter(COSTS, unknown_cost=10).segment("ក្រ")
    assert words == [Word("ក្រ", False)]


def test_empty_run():
    assert Segmenter(COSTS, unknown_cost=10).segment("") == []
