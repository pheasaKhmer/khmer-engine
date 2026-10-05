"""Find the Khmer words a romanized word could be.

Every lexicon word is indexed under several romanizations:

- "pronunciation": from its phonemic transcription, the way it sounds (mean, touch)
- "spelling": the rule-based chat style, the way it is written (pros, khmer)
- "ungegn": the UNGEGN style, for people who type standard romanization
- "curated": hand-written chat spellings, including abbreviations (jg)
- "consonants": the consonants of its chat spellings, for the most common words, which
  chat abbreviates that way (tv for ទៅ, dg for ដឹង)
- "minor": its chat spellings without the vowel of an unstressed first syllable, which
  chat often leaves out (sbay for សប្បាយ, tne for ទំនេរ)

A word with a preferred spelling (`data/preferred_spellings.tsv`) is not indexed, so
conversion writes the preferred one: ស្រឡាញ់, not ស្រលាញ់.

Lookups go by matching key (see `keys`), so spelling variants land on the same entry.
Keys one edit away are tried too. Each candidate gets an emission score, the log of how
likely the typed spelling is for that word, from two penalties: whether the key had to
be edited, and how far the typed letters are from the closest romanization of the word.
"""

from bisect import bisect_left
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from pheasa import normalize

from khmer_engine import fuzzy
from khmer_engine.keys import consonants, fold, key, without_first_vowel
from khmer_engine.lexicon import Lexicon, read_rows
from khmer_engine.phonemes import to_chat
from khmer_engine.rules import romanize_word
from khmer_engine.script import CONSONANTS, NIKAHIT

MIN_FUZZY_KEY = 3  # shorter keys have too many neighbours to edit
MIN_COMPLETION_KEY = 2  # shorter prefixes start too many words to be useful
MAX_COMPLETION_SCAN = 5000  # keys looked at per completion lookup
ABBREVIATED_WORDS = 5000  # the most common words are also indexed by their consonants


@dataclass(frozen=True)
class Weights:
    """How emission scores are made. Tuned on eval/testset.tsv."""

    key_edit: float = 5.0  # the key needed one edit
    spelling: float = 5.0  # times the normalized letter distance to the closest romanization
    curated: float = 1.5  # bonus when a hand-written chat spelling matched
    abbreviation: float = 2.0  # only the consonants of the word were typed
    minor: float = 2.0  # the vowel of the first syllable was left out
    frequency: float = 0.5  # weight of the word's log probability in `lookup`
    completion: float = 2.0  # the word is longer than what was typed so far
    missing: float = 0.5  # per key symbol not typed yet


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


def read_chat_spellings(path: Path | None = None) -> list[tuple[str, str]]:
    """Curated (spelling, Khmer word) pairs; the package's own list by default."""
    path = path or Path(str(files("khmer_engine") / "data" / "chat_spellings.tsv"))
    return [(spelling, word) for spelling, word, _ in read_rows(path, 3)]


def read_preferred_spellings(path: Path | None = None) -> dict[str, str]:
    """Each variant spelling and the spelling to write instead; the package's own list by
    default."""
    path = path or Path(str(files("khmer_engine") / "data" / "preferred_spellings.tsv"))
    return {normalize(variant): normalize(word) for variant, word, _ in read_rows(path, 3)}


def forms(word: str, pronunciations: Iterable[str], abbreviated: bool = False) -> list[Form]:
    """The romanizations a lexicon word is indexed under, without duplicates. With
    `abbreviated`, the consonants of its chat spellings too."""
    out: dict[str, Form] = {}
    for pronunciation in pronunciations:
        spelling = to_chat(pronunciation)
        out.setdefault(spelling, Form(word, spelling, "pronunciation"))
    for style, source in (("chat", "spelling"), ("ungegn", "ungegn")):
        spelling = fold(romanize_word(word, style))
        out.setdefault(spelling, Form(word, spelling, source))
    chat = [f.spelling for f in out.values() if f.source != "ungegn"]
    nasal = _minor_first_syllable(word)
    if nasal is not None:
        for short in filter(None, (without_first_vowel(s, nasal) for s in chat)):
            out.setdefault(short, Form(word, short, "minor"))
    if abbreviated:
        for abbreviation in filter(None, map(consonants, chat)):
            out.setdefault(abbreviation, Form(word, abbreviation, "consonants"))
    return list(out.values())


def _minor_first_syllable(word: str) -> bool | None:
    """Whether `word` starts with a syllable written without a vowel sign, which is
    unstressed: a consonant followed by another (សប្បាយ, រវល់), or by ំ (ទំនេរ). Returns
    whether that syllable has ំ, or None if the word does not start that way."""
    if len(word) < 3 or word[0] not in CONSONANTS:
        return None
    if word[1] in CONSONANTS:
        return False
    if word[1] == NIKAHIT and word[2] in CONSONANTS:
        return True
    return None


class Matcher:
    def __init__(
        self,
        lexicon: Lexicon,
        curated: Iterable[tuple[str, str]] = (),
        weights: Weights | None = None,
        preferred: Mapping[str, str] | None = None,
    ):
        self.lexicon = lexicon
        preferred = preferred or {}
        self.weights = weights or Weights()
        self.index: dict[str, list[Form]] = {}
        by_count = sorted(lexicon.entries.values(), key=lambda e: -e.count)
        common = {e.word for e in by_count[:ABBREVIATED_WORDS] if e.count}
        for entry in lexicon.entries.values():
            if preferred.get(entry.word) in lexicon:
                continue
            for form in forms(entry.word, entry.pronunciations, entry.word in common):
                self._add(form)
        for spelling, word in curated:
            self._add(Form(normalize(word), fold(spelling), "curated"))
        self.alphabet = sorted({symbol for k in self.index for symbol in k})
        self.sorted_keys = sorted(self.index)

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
            elif form.source == "consonants":
                score -= self.weights.abbreviation
            elif form.source == "minor":
                score -= self.weights.minor
            if form.word not in best or score > best[form.word][0]:
                best[form.word] = (score, form)
        return best

    def completions(self, text: str, limit: int = 20) -> dict[str, tuple[float, Form]]:
        """Words whose key starts with the key of `text` and is longer: readings of a word
        still being typed. Exact keys are left to `emissions`. Keeps the `limit` words
        with the best emission and frequency."""
        prefix = key(text, final=False)
        if len(prefix) < MIN_COMPLETION_KEY:
            return {}
        found: dict[str, tuple[float, Form]] = {}
        start = bisect_left(self.sorted_keys, prefix)
        for other in self.sorted_keys[start : start + MAX_COMPLETION_SCAN]:
            if not other.startswith(prefix):
                break
            if other == prefix:
                continue
            score = -self.weights.completion - self.weights.missing * (len(other) - len(prefix))
            for form in self.index[other]:
                if form.word not in found or score > found[form.word][0]:
                    found[form.word] = (score, form)
        ranked = sorted(
            found.items(),
            key=lambda item: -(item[1][0] + self.weights.frequency * self.lexicon.logprob(item[0])),
        )
        return dict(ranked[:limit])

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
