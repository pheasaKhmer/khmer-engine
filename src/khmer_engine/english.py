"""English words that stay in Latin letters among romanized Khmer."""

from importlib.resources import files
from pathlib import Path


def read_english(path: Path | None = None) -> frozenset[str]:
    """Lowercase English words, one per line; the package's own list by default."""
    path = path or Path(str(files("khmer_engine") / "data" / "english.txt"))
    words = (line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines())
    return frozenset(w for w in words if w and not w.startswith("#"))
