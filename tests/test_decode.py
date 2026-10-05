import pytest

from khmer_engine.decode import Choice, Decoder, _Phrase, _segments, join
from khmer_engine.lexicon import Lexicon


def test_segments_split_phrases_from_the_text_between_them():
    pieces = list(_segments("sok sabay te? ok\n12 ខ្ញុំ"))
    phrases = [p for p in pieces if isinstance(p, _Phrase)]
    assert [[w[0] for w in p.words] for p in phrases] == [["sok", "sabay", "te"], ["ok"]]
    assert "".join(p if isinstance(p, str) else "#" for p in pieces) == "#? #\n12 ខ្ញុំ"


def test_segments_keep_character_offsets():
    (space, phrase) = _segments("  Kâmpŭchéa l'or")
    assert space == "  "
    assert phrase.words == [("Kâmpŭchéa", 2, 11), ("l'or", 12, 16)]


def test_join_writes_khmer_together_and_english_apart():
    choices = [
        Choice("អត់", 0, "pronunciation"),
        Choice("មាន", 0, "pronunciation"),
        Choice("wifi", 0, "english"),
        Choice("ទេ", 0, "pronunciation"),
    ]
    assert join(choices) == "អត់មាន wifi ទេ"


@pytest.fixture
def decoder():
    lexicon = Lexicon(
        {w: e for w, e in Lexicon.sample().entries.items() if w in {"បង", "បង់", "ស្រឡាញ់", "លុយ"}},
        {("បង", "ស្រឡាញ់"): 50, ("បង់", "លុយ"): 50},
    )
    table = {
        "bong": [Choice("បង", -0.5, "pronunciation"), Choice("បង់", -0.5, "pronunciation")],
        "srolanh": [Choice("ស្រឡាញ់", 0.0, "pronunciation")],
        "luy": [Choice("លុយ", 0.0, "pronunciation")],
    }
    return Decoder(lexicon, lambda typed, whole: table.get(typed, []))


def test_the_next_word_decides_between_homophones(decoder):
    assert decoder.convert("bong srolanh").text == "បងស្រឡាញ់"
    assert decoder.convert("bong luy").text == "បង់លុយ"


def test_tokens_put_the_chosen_reading_first(decoder):
    (bong, luy) = decoder.convert("bong luy").tokens
    assert (bong.typed, bong.start, bong.end) == ("bong", 0, 4)
    assert [c.text for c in bong.choices] == ["បង់", "បង"]
    assert luy.choices[0].text == "លុយ"


def test_text_without_any_reading_is_kept(decoder):
    assert decoder.convert("xyz bong").text == "xyz bong"


def test_phrase_positions_count_letters_without_spaces():
    (phrase,) = _segments("or kunbong")
    assert phrase.offsets() == [0, 2, 9]
    assert phrase.typed(0, 5) == "or kun"
    assert phrase.characters(0, 5) == (0, 6)
    assert phrase.typed(5, 9) == "bong"
    assert phrase.characters(5, 9) == (6, 10)
