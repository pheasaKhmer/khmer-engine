from khmer_engine.english import read_english


def test_packaged_list():
    words = read_english()
    assert {"ok", "wifi", "facebook", "send"} <= words
    # Common chat spellings of Khmer words are left out.
    assert not {"mean", "ban", "men", "the"} & words


def test_custom_list(tmp_path):
    path = tmp_path / "english.txt"
    path.write_text("# comment\nHello\n\n  wifi \n", encoding="utf-8")
    assert read_english(path) == {"hello", "wifi"}
