"""Romanize Khmer text: split it into words, then romanize each word.

Khmer is normalized with pheasa first (Khmer digits become ASCII digits and zero-width
spaces become spaces), then each run of Khmer letters is segmented into lexicon words.
In the "chat" style a word the lexicon can pronounce is spelled from its pronunciation,
the way people type it, with the aspiration of a first consonant taken from the
spelling; other words, and every word in the "ungegn" style, are romanized from their
spelling. Words are separated by spaces. Khmer punctuation becomes
Latin punctuation, and ៗ repeats the word before it.
"""

import math
from typing import Literal

from pheasa import normalize

from khmer_engine.lexicon import Lexicon
from khmer_engine.phonemes import to_chat
from khmer_engine.rules import romanize_word
from khmer_engine.script import LEK_TOO
from khmer_engine.segment import KHMER_RUN, Segmenter, Word
from khmer_engine.syllables import clusters

Style = Literal["chat", "ungegn"]

PUNCTUATION = {"។": ".", "៕": ".", "៖": ":", "៘": "...", "៚": "...", "៙": "", "៛": " riel"}

# Longest first, so chh is tried before ch.
_ASPIRATED = (("chh", "ch"), ("ph", "p"), ("th", "t"), ("kh", "k"))


def _aspirate(spoken: str, written: str) -> str:
    """Pronunciations drop the aspiration of the first consonant of a cluster (ភ្នំ is
    /pnum/), but people type it from the spelling: "phnum", "khnhom", "thngai"."""
    for aspirated, plain in _ASPIRATED:
        if written.startswith(aspirated) and spoken.startswith(plain):
            return spoken if spoken.startswith(aspirated) else aspirated + spoken[len(plain) :]
    return spoken


def _is_letter(word: Word) -> bool:
    """A single consonant cluster without a vowel, such as ក or ក្រ: the lexicon has them
    as words (letter names), but next to unknown text they are usually part of it."""
    parts = clusters(word.text)
    return len(parts) == 1 and not parts[0].has_nucleus


def merge_unknown(words: list[Word]) -> list[Word]:
    """Join each unknown word with the bare letters around it, so ចក្រពត្តិ is romanized
    as one word rather than as letter names around an unknown piece."""
    out: list[Word] = []
    group: list[Word] = []

    def flush() -> None:
        if any(not w.known for w in group):
            out.append(Word("".join(w.text for w in group), known=False))
        else:
            out.extend(group)
        group.clear()

    for word in words:
        if not word.known or _is_letter(word):
            group.append(word)
        else:
            flush()
            out.append(word)
    flush()
    return out


def _append(out: list[str], piece: str) -> None:
    """Add `piece`, with a space if it would otherwise run into the previous word."""
    if out and piece and out[-1][-1:].isalnum() and piece[0].isalnum():
        out.append(" ")
    out.append(piece)


class Romanizer:
    def __init__(self, lexicon: Lexicon):
        self.lexicon = lexicon
        costs = {word: -lexicon.logprob(word) for word in lexicon.entries}
        unknown = -math.log(1 / (lexicon.total + len(lexicon) + 1)) + 4.0
        self.segmenter = Segmenter(costs, unknown_cost=unknown)

    def word(self, word: str, style: Style = "chat") -> str:
        """Romanize one Khmer word."""
        written = romanize_word(word, style)
        if style == "chat":
            entry = self.lexicon.entries.get(word)
            if entry and entry.pronunciations:
                return _aspirate(to_chat(entry.pronunciations[0]), written)
        return written

    def romanize(self, text: str, style: Style = "chat") -> str:
        """Romanize Khmer text, leaving anything that is not Khmer as it is."""
        text = normalize(text, digits="ascii", zwsp="space")
        out: list[str] = []
        last_word = ""
        position = 0
        for run in KHMER_RUN.finditer(text):
            last_word = self._between(out, text[position : run.start()], last_word)
            pieces = merge_unknown(self.segmenter.segment(run.group()))
            words = [self.word(w.text, style) for w in pieces]
            _append(out, " ".join(words))
            last_word = words[-1]
            position = run.end()
        self._between(out, text[position:], last_word)
        return "".join(out)

    @staticmethod
    def _between(out: list[str], text: str, last_word: str) -> str:
        for i, ch in enumerate(text):
            if ch == LEK_TOO and last_word:
                _append(out, " " + last_word)
            elif ch in PUNCTUATION:
                out.append(PUNCTUATION[ch])
            else:
                if i == 0:
                    _append(out, ch)  # only the first character can touch a Khmer word
                else:
                    out.append(ch)
                if not ch.isspace():
                    last_word = ""
        return last_word
