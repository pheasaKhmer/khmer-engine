"""Transliterate romanized words the lexicon does not know, syllable by syllable.

The syllable table is learned from the lexicon: for every word whose pronunciation has
as many syllables as its spelling, each spoken syllable is paired with the written
syllable it comes from, and counted once per word under the matching key of its chat
spelling. Counting words rather than uses keeps very common words such as ការ from
deciding how every "ka" is spelled. An unknown word is split into the sequence of
known syllable keys with the highest total log probability, and each piece is written
with its most common spelling. The result is a plausible Khmer spelling, not a
dictionary one, so names and new words still come out readable.
"""

import math
from collections import Counter

from khmer_engine.keys import fold, key
from khmer_engine.lexicon import Lexicon
from khmer_engine.phonemes import to_chat
from khmer_engine.script import COENG
from khmer_engine.syllables import syllables

MAX_SYLLABLE_LETTERS = 7
# Inside a word, a syllable seldom starts with a vowel: "dara" is da-ra, not dar-a.
VOWEL_ONSET_COST = 3.0


class Transliterator:
    def __init__(self, table: dict[str, Counter[str]]):
        self.spelling = {k: spellings.most_common(1)[0][0] for k, spellings in table.items()}
        counts = {k: sum(spellings.values()) for k, spellings in table.items()}
        total = sum(counts.values()) or 1
        self.logprob = {k: math.log(n / total) for k, n in counts.items()}

    @classmethod
    def from_lexicon(cls, lexicon: Lexicon) -> "Transliterator":
        table: dict[str, Counter[str]] = {}
        for entry in lexicon.entries.values():
            written = syllables(entry.word)
            for pronunciation in entry.pronunciations:
                spoken = pronunciation.split(" . ")
                if len(spoken) != len(written):
                    continue
                for sound, syllable in zip(spoken, written, strict=True):
                    sound_key = key(to_chat(sound))
                    text = syllable.text.lstrip(COENG)  # a subscript onset, written in full
                    if sound_key and text:
                        table.setdefault(sound_key, Counter())[text] += 1
        return cls(table)

    def transliterate(self, typed: str) -> str | None:
        """Khmer for `typed` built from known syllables, or None if they cannot cover it."""
        letters = fold(typed)
        if not letters:
            return None
        best: list[tuple[float, int, str] | None] = [(0.0, 0, "")] + [None] * len(letters)
        for start in range(len(letters)):
            if best[start] is None:
                continue
            for end in range(start + 1, min(start + MAX_SYLLABLE_LETTERS, len(letters)) + 1):
                piece_key = key(letters[start:end], final=end == len(letters))
                if piece_key not in self.spelling:
                    continue
                score = best[start][0] + self.logprob[piece_key]
                if start and letters[start] in "aeiou":
                    score -= VOWEL_ONSET_COST
                if best[end] is None or score > best[end][0]:
                    best[end] = (score, start, self.spelling[piece_key])
        if best[-1] is None:
            return None
        pieces = []
        end = len(letters)
        while end:
            _, start, text = best[end]
            pieces.append(text)
            end = start
        return "".join(reversed(pieces))
