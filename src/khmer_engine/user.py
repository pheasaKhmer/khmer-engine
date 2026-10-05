"""What the user picked before, so it ranks higher next time.

Picks are counted per matching key of the typed text, so a choice made for "sok" also
counts for "sork". They live in memory and, if a path is given, in a local JSON file.
Nothing is sent anywhere.
"""

import json
import os
import tempfile
from pathlib import Path

from khmer_engine.keys import key


class UserDictionary:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else None
        self.counts: dict[str, dict[str, int]] = {}
        if self.path and self.path.exists():
            self.counts = json.loads(self.path.read_text(encoding="utf-8"))

    def learn(self, typed: str, word: str) -> None:
        """Record that `word` was picked for `typed`."""
        typed_key = key(typed)
        if not typed_key or not word:
            return
        picks = self.counts.setdefault(typed_key, {})
        picks[word] = picks.get(word, 0) + 1
        self._save()

    def picks(self, typed: str) -> dict[str, int]:
        """How often each word was picked for text with the same key as `typed`."""
        return self.counts.get(key(typed), {})

    def clear(self) -> None:
        """Forget every pick, and delete the file."""
        self.counts = {}
        if self.path and self.path.exists():
            self.path.unlink()

    def _save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write a temporary file and rename it, so a crash never leaves half a file.
        handle, temporary = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(self.counts, out, ensure_ascii=False, indent=1, sort_keys=True)
        Path(temporary).replace(self.path)
