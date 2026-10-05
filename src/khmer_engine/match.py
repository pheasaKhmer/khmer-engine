"""Find the Khmer words a romanized word could be.

Every lexicon word is indexed under several romanizations:

- "pronunciation": from its phonemic transcription, the way it sounds (mean, touch)
- "spelling": the rule-based chat style, the way it is written (pros, khmer)
- "ungegn": the UNGEGN style, for people who type standard romanization
- "curated": hand-written chat spellings, including abbreviations (jg)

Lookups go by matching key (see `keys`), so spelling variants land on the same entry.
Keys one edit away are tried too. Each candidate gets an emission score, the log of how
likely the typed spelling is for that word, from two penalties: whether the key had to
be edited, and how far the typed letters are from the closest romanization of the word.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from pheasa import normalize

from khmer_engine import fuzzy
from khmer_engine.keys import fold, key
from khmer_engine.lexicon import Lexicon
from khmer_engine.phonemes import to_chat
from khmer_engine.rules import romanize_word

MIN_FUZZY_KEY = 3  # shorter keys have too many neighbours to edit


@dataclass(frozen=True)
class Weights:
    """How emission scores are made. Tuned on eval/testset.tsv."""

    key_edit: float = 5.0  # the key needed one edit
    spelling: float = 5.0  # times the normalized letter distance to the closest romanization
    curated: float = 1.5  # bonus when a hand-written chat spelling matched
    frequency: float = 0.5  # weight of the word's log probability in `lookup`


@dataclass(frozen=True)
class Form:
    """A romanization of `word` from `source`."""

    word: str
    spelling: str
    source: str


@dataclass(frozen=True)
class Candidate:
    """A Khmer reading of some romanized text. Higher scores are better."""

    text: str
    score: float
    spelling: str
    source: str


def forms(word: str, pronunciations: Iterable[str]) -> list[Form]:
    """The romanizations a lexicon word is indexed under, without duplicates."""
    out: dict[str, Form] = {}
    for pronunciation in pronunciations:
        spelling = to_chat(pronunciation)
        out.setdefault(spelling, Form(word, spelling, "pronunciation"))
    for style, source in (("chat", "spelling"), ("ungegn", "ungegn")):
        spelling = fold(romanize_word(word, style))
        out.setdefault(spelling, Form(word, spelling, source))
    return list(out.values())


class Matcher:
    def __init__(
        self,
        lexicon: Lexicon,
        curated: Iterable[tuple[str, str]] = (),
        weights: Weights | None = None,
    ):
        self.lexicon = lexicon
        self.weights = weights or Weights()
        self.index: dict[str, list[Form]] = {}
        for entry in lexicon.entries.values():
            for form in forms(entry.word, entry.pronunciations):
                self._add(form)
        for spelling, word in curated:
            self._add(Form(normalize(word), fold(spelling), "curated"))
        self.alphabet = sorted({symbol for k in self.index for symbol in k})

    def _add(self, form: Form) -> None:
        self.index.setdefault(key(form.spelling), []).append(form)

    def emissions(self, text: str, *, fuzzy_keys: bool = True) -> dict[str, tuple[float, Form]]:
        """Each candidate word with its emission score and the form that matched best."""
        typed = fold(text)
        typed_key = key(typed)
        if not typed_key:
            return {}
        hits: list[tuple[Form, int]] = [(f, 0) for f in self.index.get(typed_key, ())]
        if fuzzy_keys and len(typed_key) >= MIN_FUZZY_KEY:
            seen = {typed_key}
            for other in fuzzy.neighbours(typed_key, self.alphabet):
                if other not in seen:
                    seen.add(other)
                    hits.extend((f, 1) for f in self.index.get(other, ()))
        best: dict[str, tuple[float, Form]] = {}
        for form, key_edits in hits:
            letters = fuzzy.distance(typed, form.spelling)
            score = -self.weights.key_edit * key_edits
            score -= self.weights.spelling * letters / max(len(typed), len(form.spelling))
            if form.source == "curated":
                score += self.weights.curated
            if form.word not in best or score > best[form.word][0]:
                best[form.word] = (score, form)
        return best

    def lookup(self, text: str, n: int = 5) -> list[Candidate]:
        """The `n` most likely Khmer words for one romanized word, with no context."""
        ranked = [
            Candidate(
                word,
                emission + self.weights.frequency * self.lexicon.logprob(word),
                form.spelling,
                form.source,
            )
            for word, (emission, form) in self.emissions(text).items()
        ]
        ranked.sort(key=lambda c: (-c.score, c.text))
        return ranked[:n]
