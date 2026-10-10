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
        ("bong srolanh", "បងស្រឡាញ់"),  # the preferred spelling, not ស្រលាញ់
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
        ("good morning", "good morning"),  # not split into mor (មក) and ning (និង)
    ],
)
def test_english_words_stay_in_latin_letters(engine, typed, expected):
    assert engine.convert(typed) == expected


def test_words_on_the_english_list_can_still_be_khmer():
    # Keeping a word in English has a cost, so a good Khmer reading in context wins.
    assert Engine(english=frozenset({"te"})).convert("ot mean te") == "អត់មានទេ"


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("soksabayte", "សុខសប្បាយទេ"),
        ("orkunbong", "អរគុណបង"),
        ("nhambayhoynov", "ញ៉ាំបាយហើយនៅ"),
        # A one-letter abbreviation inside a typed word.
        ("bsrey", "បងស្រី"),
        ("orkunb", "អរគុណបង"),
    ],
)
def test_words_typed_without_spaces_are_split(engine, typed, expected):
    assert engine.convert(typed) == expected


def test_split_tokens_point_inside_the_typed_word(engine):
    tokens = engine.analyze("ot orkunbong").tokens
    assert [(t.typed, t.start, t.end) for t in tokens] == [
        ("ot", 0, 2),
        ("orkun", 3, 8),
        ("bong", 8, 12),
    ]


def test_unknown_words_are_transliterated(engine):
    result = engine.analyze("knhom chmous sreymom")
    assert result.text == "ខ្ញុំឈ្មោះស្រីមុំ"
    assert result.tokens[-1].choices[0].source == "fallback"


def test_words_nothing_can_read_are_kept(engine):
    assert engine.convert("xyzq bong") == "xyzq បង"


def test_suggest_completes_the_word_being_typed(engine):
    (first, *_) = engine.suggest("orku")
    assert (first.text, first.source, first.start, first.end) == ("អរគុណ", "completion", 0, 4)


def test_suggest_gives_the_span_to_replace(engine):
    (first, *_) = engine.suggest("sok saba")
    assert (first.text, first.start, first.end) == ("សុខសប្បាយ", 0, 8)


def test_suggest_ranks_readings_of_the_last_word_in_context(engine):
    suggestions = engine.suggest("sok sabay te", n=3)
    assert suggestions[0].text == "ទេ"
    assert len(suggestions) == 3
    assert all((s.start, s.end) == (10, 12) for s in suggestions)
    assert [s.score for s in suggestions] == sorted((s.score for s in suggestions), reverse=True)


def test_a_finished_word_is_not_completed(engine):
    assert all(s.source != "completion" for s in engine.suggest("hello?"))


def test_suggest_without_latin_words(engine):
    assert engine.suggest("") == []
    assert engine.suggest("123 ?") == []
