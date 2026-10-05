import khmer_engine


def test_convert():
    assert khmer_engine.convert("sok sabay te") == "សុខសប្បាយទេ"


def test_suggest():
    suggestions = khmer_engine.suggest("sok sabay", n=3)
    assert suggestions[0].text == "សុខសប្បាយ"
    assert len(suggestions) <= 3


def test_default_engine_loads_the_data_directory_from_the_environment(tmp_path, monkeypatch):
    (tmp_path / "lexicon.tsv").write_text("សុខ\t1\ts o k\n", encoding="utf-8")
    monkeypatch.setenv("KHMER_ENGINE_DATA", str(tmp_path))
    khmer_engine.default_engine.cache_clear()
    try:
        assert len(khmer_engine.default_engine().lexicon) == 1
    finally:
        khmer_engine.default_engine.cache_clear()


def test_romanize():
    assert khmer_engine.romanize("សុខសប្បាយទេ") == "soksabay te"
    assert khmer_engine.romanize("សុខសប្បាយទេ", "ungegn") == "sŏkhsâbbay té"
