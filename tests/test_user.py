import json

from khmer_engine.decode import Choice
from khmer_engine.engine import Engine
from khmer_engine.user import UserDictionary


def test_picks_are_counted_by_matching_key_and_previous_word():
    user = UserDictionary()
    user.learn("sok", "សុខ")
    user.learn("sork", "សុខ")
    user.learn("sok", "សុខ", previous="ខ្ញុំ")
    assert user.picks("sok") == {"": {"សុខ": 2}, "ខ្ញុំ": {"សុខ": 1}}
    assert user.picks("bong") == {}


def test_empty_input_is_not_learned():
    user = UserDictionary()
    user.learn("123", "ក")
    user.learn("sok", "")
    assert user.counts == {}


def test_picks_are_saved_and_loaded(tmp_path):
    path = tmp_path / "nested" / "picks.json"
    UserDictionary(path).learn("bong", "បង់", previous="ការ")
    assert json.loads(path.read_text(encoding="utf-8")) == {"bON": {"ការ": {"បង់": 1}}}
    assert UserDictionary(path).picks("bong") == {"ការ": {"បង់": 1}}


def test_picks_saved_without_previous_words_still_load(tmp_path):
    path = tmp_path / "picks.json"
    path.write_text(json.dumps({"bON": {"បង់": 2}}), encoding="utf-8")
    assert UserDictionary(path).picks("bong") == {"": {"បង់": 2}}


def test_clear_forgets_and_deletes_the_file(tmp_path):
    path = tmp_path / "picks.json"
    user = UserDictionary(path)
    user.learn("bong", "បង់")
    user.clear()
    assert user.picks("bong") == {}
    assert not path.exists()


def test_a_picked_word_ranks_higher_next_time():
    engine = Engine()
    assert engine.suggest("bong")[0].text == "បង"
    engine.learn("bong", "បង់")
    engine.learn("bong", "បង់")
    assert engine.suggest("bong")[0].text == "បង់"
    assert engine.suggest("borng")[0].text == "បង់"  # same key


def test_a_picked_word_the_lexicon_lacks_is_offered():
    engine = Engine()
    engine.learn("dararith", "ដារ៉ារិទ្ធ")
    first = engine.suggest("knhom chmous dararith")[0]
    assert (first.text, first.source) == ("ដារ៉ារិទ្ធ", "learned")


def test_a_picked_word_spelled_like_the_guess_is_still_learned():
    engine = Engine()
    guess = engine.transliterator.transliterate("dararith")
    assert guess and guess not in engine.lexicon
    engine.learn("dararith", guess, previous="ឈ្មោះ")
    readings = [c for c in engine.choices("dararith") if c.text == guess]
    assert [c.source for c in readings] == ["learned"]
    assert engine.suggest("knhom chmous dararith")[0].text == guess


def test_a_pick_counts_most_after_the_same_word():
    engine = Engine()
    for _ in range(3):
        engine.learn("te", "តេ", previous="ចាំ")
    assert engine.convert("jam te tv vinh") == "ចាំតេទៅវិញ"
    assert engine.convert("ot mean te") == "អត់មានទេ"


def test_elsewhere_each_previous_word_counts_once():
    engine = Engine()
    te = Choice("តេ", 0.0, "pronunciation")
    engine.learn("te", "តេ", previous="ចាំ")
    once = engine.learned_bonus("មាន", "te", te)
    for _ in range(4):
        engine.learn("te", "តេ", previous="ចាំ")
    assert engine.learned_bonus("មាន", "te", te) == once > 0
    assert engine.learned_bonus("ចាំ", "te", te) > once
    engine.learn("te", "តេ", previous="ហៅ")
    assert engine.learned_bonus("មាន", "te", te) > once
