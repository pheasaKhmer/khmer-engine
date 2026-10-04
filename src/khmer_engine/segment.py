"""Split Khmer text into words with a dictionary and dynamic programming.

Khmer is written without spaces between words. `Segmenter` finds the split into
dictionary words with the lowest total cost (minus log probability, so frequent words
are preferred). Words never start or end inside a written cluster. Text the dictionary
cannot cover is returned as unknown words, one per unbroken unknown run.
"""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from khmer_engine.script import COENG

# A cluster starts at every base letter (consonant or independent vowel) that is not a
# subscript, i.e. not written after a coeng.
_CLUSTER_START = re.compile(f"(?<!{COENG})[\u1780-\u17b3]")

# Characters that belong to Khmer words: letters, vowels, signs and joiners.
KHMER_RUN = re.compile("[\u1780-\u17d3\u17dd\u200c\u200d]+")


def cluster_starts(text: str) -> list[int]:
    """Offsets where a written cluster starts, plus the end of the text."""
    starts = [m.start() for m in _CLUSTER_START.finditer(text)]
    if not starts or starts[0] != 0:
        starts.insert(0, 0)
    starts.append(len(text))
    return starts


@dataclass(frozen=True)
class Word:
    text: str
    known: bool


class Segmenter:
    """Segment normalized Khmer runs. `costs` maps each word to its cost."""

    def __init__(self, costs: Mapping[str, float], unknown_cost: float, max_clusters: int = 12):
        self.costs = costs
        self.unknown_cost = unknown_cost
        self.max_clusters = max_clusters
        # Every cluster-aligned prefix of a word, so the search can stop early.
        self._prefixes: set[str] = set()
        for word in costs:
            bounds = cluster_starts(word)
            self._prefixes.update(word[: bounds[i]] for i in range(1, len(bounds)))

    def segment(self, run: str) -> list[Word]:
        """Split one run of Khmer letters (no spaces or punctuation) into words."""
        if not run:
            return []
        bounds = cluster_starts(run)
        n = len(bounds) - 1
        best = [0.0] + [float("inf")] * n
        back: list[tuple[int, bool]] = [(0, False)] * (n + 1)
        for i in range(n):
            if best[i] == float("inf"):
                continue
            # One unknown cluster always works, so every position stays reachable.
            unknown = best[i] + self.unknown_cost
            if unknown < best[i + 1]:
                best[i + 1], back[i + 1] = unknown, (i, False)
            for j in range(i + 1, min(i + self.max_clusters, n) + 1):
                piece = run[bounds[i] : bounds[j]]
                if piece not in self._prefixes:
                    break
                cost = self.costs.get(piece)
                if cost is not None and best[i] + cost < best[j]:
                    best[j], back[j] = best[i] + cost, (i, True)
        return list(self._words(run, bounds, back))

    @staticmethod
    def _words(run: str, bounds: list[int], back: list[tuple[int, bool]]) -> Iterator[Word]:
        pieces: list[Word] = []
        j = len(bounds) - 1
        while j > 0:
            i, known = back[j]
            pieces.append(Word(run[bounds[i] : bounds[j]], known))
            j = i
        pieces.reverse()
        # Merge neighbouring unknown clusters into one unknown word.
        pending = ""
        for piece in pieces:
            if piece.known:
                if pending:
                    yield Word(pending, False)
                    pending = ""
                yield piece
            else:
                pending += piece.text
        if pending:
            yield Word(pending, False)
