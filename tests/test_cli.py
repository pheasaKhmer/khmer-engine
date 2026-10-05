import io
import subprocess
import sys

from khmer_engine.cli import main


def run(capsys, *argv: str) -> str:
    assert main(list(argv)) == 0
    return capsys.readouterr().out


def test_convert(capsys):
    assert run(capsys, "convert", "sok", "sabay", "te") == "សុខសប្បាយទេ\n"


def test_convert_reads_standard_input(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("orkun\not mean te\n"))
    assert run(capsys, "convert") == "អរគុណ\nអត់មានទេ\n"


def test_suggest(capsys):
    lines = run(capsys, "suggest", "-n", "2", "orku").splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("1. អរគុណ\t")


def test_romanize(capsys):
    assert run(capsys, "romanize", "សុខសប្បាយទេ") == "soksabay te\n"
    assert run(capsys, "romanize", "--style", "ungegn", "សុខសប្បាយទេ") == "sŏkhsâbbay té\n"


def test_repl(capsys, monkeypatch, tmp_path):
    picks = tmp_path / "picks.json"
    lines = iter(["sok sabay te", ":k ទេ", ":learn bong បង់", "bong", ":q"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(lines))
    out = run(capsys, "--user", str(picks), "repl")
    assert "សុខសប្បាយទេ" in out
    assert "chat:   te" in out
    assert "learned បង់ for bong" in out
    assert "bong: 1.បង់" in out
    assert picks.exists()


def test_data_directory_option(capsys, tmp_path):
    (tmp_path / "lexicon.tsv").write_text("សុខ\t1\ts o k\n", encoding="utf-8")
    assert run(capsys, "--data", str(tmp_path), "convert", "sok") == "សុខ\n"


def test_runs_as_a_module():
    result = subprocess.run(
        [sys.executable, "-m", "khmer_engine", "convert", "orkun"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert result.stdout == "អរគុណ\n"
