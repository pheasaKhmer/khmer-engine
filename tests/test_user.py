import json

from khmer_engine.engine import Engine
from khmer_engine.user import UserDictionary


def test_picks_are_counted_by_matching_key():
    user = UserDictionary()
    user.learn("sok", "សុខ")
    user.learn("sork", "សុខ")
    assert user.picks("sok") == {"សុខ": 2}
    assert user.picks("bong") == {}


def test_empty_input_is_not_learned():
    user = UserDictionary()
    user.learn("123", "ក")
    user.learn("sok", "")
    assert user.counts == {}


def test_picks_are_saved_and_loaded(tmp_path):
    path = tmp_path / "nested" / "picks.json"
    UserDictionary(path).learn("bong", "បង់")
    assert json.loads(path.read_text(encoding="utf-8")) == {"bON": {"បង់": 1}}
    assert UserDictionary(path).picks("bong") == {"បង់": 1}


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
