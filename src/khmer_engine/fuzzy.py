"""Edit distance and edit neighbourhoods for fuzzy matching."""

from collections.abc import Iterable, Iterator


def distance(a: str, b: str) -> int:
    """Optimal string alignment distance: insertions, deletions, substitutions and
    swaps of two neighbouring letters each cost 1."""
    if a == b:
        return 0
    if not a or not b:
        return len(a) or len(b)
    previous2: list[int] = []
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            current[j] = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (ca != cb),
            )
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                current[j] = min(current[j], previous2[j - 2] + 1)
        previous2, previous = previous, current
    return previous[-1]


def neighbours(word: str, alphabet: Iterable[str]) -> Iterator[str]:
    """Every string one edit away from `word` (it may yield duplicates)."""
    letters = list(alphabet)
    for i in range(len(word) + 1):
        head, tail = word[:i], word[i:]
        for letter in letters:
            yield head + letter + tail  # insertion
        if tail:
            yield head + tail[1:]  # deletion
            for letter in letters:
                if letter != tail[0]:
                    yield head + letter + tail[1:]  # substitution
            if len(tail) > 1:
                yield head + tail[1] + tail[0] + tail[2:]  # swap
