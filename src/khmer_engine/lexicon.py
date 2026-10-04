"""The word list and frequencies the engine works from.

A lexicon directory holds tab-separated UTF-8 files. Lines starting with "#" are
comments.

- `lexicon.tsv`: word, corpus count, pronunciations (phonemic transcriptions separated
  by "|"; empty when unknown). Required.
- `bigrams.tsv`: word, next word, corpus count. Optional.

Words are normalized with pheasa when loaded, so lookups must normalize too.
"""

import math
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pheasa import normalize


@dataclass(frozen=True)
class Entry:
    word: str
    count: int
    pronunciations: tuple[str, ...] = ()


def read_rows(path: Path, columns: int) -> Iterator[list[str]]:
    """Yield the tab-separated fields of each data line, padded to `columns`."""
    with path.open(encoding="utf-8") as lines:
        for number, line in enumerate(lines, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) > columns:
                raise ValueError(f"{path}:{number}: expected at most {columns} fields")
            yield fields + [""] * (columns - len(fields))


@dataclass
class Lexicon:
    entries: dict[str, Entry]
    bigrams: dict[tuple[str, str], int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.total = sum(e.count for e in self.entries.values())
        self._following: dict[str, int] = {}
        for (first, _), count in self.bigrams.items():
            self._following[first] = self._following.get(first, 0) + count

    def __contains__(self, word: str) -> bool:
        return word in self.entries

    def __len__(self) -> int:
        return len(self.entries)

    def logprob(self, word: str) -> float:
        """Smoothed log unigram probability (add-one), defined for unknown words too."""
        count = self.entries[word].count if word in self.entries else 0
        return math.log((count + 1) / (self.total + len(self.entries) + 1))

    def bigram_logprob(self, previous: str, word: str, weight: float = 0.7) -> float:
        """Log P(word | previous), interpolated with the unigram probability."""
        unigram = math.exp(self.logprob(word))
        following = self._following.get(previous, 0)
        if not following:
            return math.log(unigram)
        bigram = self.bigrams.get((previous, word), 0) / following
        return math.log(weight * bigram + (1 - weight) * unigram)

    @classmethod
    def load(cls, directory: Path | str) -> "Lexicon":
        directory = Path(directory)
        entries: dict[str, Entry] = {}
        for word, count, pronunciations in read_rows(directory / "lexicon.tsv", 3):
            word = normalize(word)
            prons = tuple(p for p in pronunciations.split("|") if p)
            if word in entries:  # two spellings that normalize to the same word
                old = entries[word]
                prons = old.pronunciations + tuple(p for p in prons if p not in old.pronunciations)
                entries[word] = Entry(word, old.count + int(count or 0), prons)
            else:
                entries[word] = Entry(word, int(count or 0), prons)
        bigrams: dict[tuple[str, str], int] = {}
        bigram_path = directory / "bigrams.tsv"
        if bigram_path.exists():
            for first, second, count in read_rows(bigram_path, 3):
                key = (normalize(first), normalize(second))
                bigrams[key] = bigrams.get(key, 0) + int(count)
        return cls(entries, bigrams)
