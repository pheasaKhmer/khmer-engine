"""The conversion engine: lexicon, matcher and decoder together."""

import gc
import math
from dataclasses import dataclass
from functools import cached_property

from khmer_engine.decode import Choice, Conversion, Decoder, Settings
from khmer_engine.english import read_english
from khmer_engine.lexicon import Lexicon
from khmer_engine.match import Matcher, Weights, read_chat_spellings, read_preferred_spellings
from khmer_engine.romanize import Romanizer, Style
from khmer_engine.transliterate import Transliterator
from khmer_engine.user import UserDictionary

# Emission of a syllable-by-syllable transliteration: it is a guess, so any reasonable
# lexicon reading should beat it.
FALLBACK_EMISSION = -8.0
# Emission of keeping a typed word as it is, when nothing else reads it.
TYPED_EMISSION = -20.0
# Bonus per log(1 + times picked) for what the user picked before for the same key.
LEARNED_WEIGHT = 3.0
# Extra bonus for a picked Khmer word the lexicon lacks, which the language model
# would otherwise treat as unseen.
LEARNED_UNKNOWN_BONUS = 5.0
# Span readings kept between calls. A keyboard calls suggest on every keystroke, and
# most spans of the input are the same as on the previous call.
CHOICE_CACHE_SIZE = 4096


@dataclass(frozen=True)
class Suggestion:
    """A reading for the word being typed. Replacing `text[start:end]` of the input with
    `text` commits it. Higher scores are better."""

    text: str
    score: float
    start: int
    end: int
    source: str


class Engine:
    """Converts romanized Khmer to Khmer script.

    By default it uses the sample lexicon shipped with the package, the curated chat
    spellings, the preferred spellings and the English word list. Pass
    `Lexicon.load("data/build")` for the full lexicon.
    """

    def __init__(
        self,
        lexicon: Lexicon | None = None,
        *,
        chat_spellings: list[tuple[str, str]] | None = None,
        preferred_spellings: dict[str, str] | None = None,
        english: frozenset[str] | None = None,
        weights: Weights | None = None,
        settings: Settings | None = None,
        user: UserDictionary | None = None,
    ):
        self.lexicon = lexicon or Lexicon.sample()
        spellings = read_chat_spellings() if chat_spellings is None else chat_spellings
        if preferred_spellings is None:
            preferred_spellings = read_preferred_spellings()
        self.matcher = Matcher(self.lexicon, spellings, weights, preferred_spellings)
        self.english = read_english() if english is None else english
        self.transliterator = Transliterator.from_lexicon(self.lexicon)
        self.user = user or UserDictionary()
        self._choice_cache: dict[tuple[str, bool], list[Choice]] = {}
        # The lexicon and indexes never change after this point. Taking them out of
        # garbage collection keeps a full collection, which would walk millions of
        # objects, from pausing a keystroke for tens of milliseconds.
        gc.freeze()
        self.decoder = Decoder(self.lexicon, self.choices, settings)

    def choices(self, typed: str, whole: bool = True) -> list[Choice]:
        """Every reading of one span of typed text, with its emission score. A piece of a
        typed word (`whole` false) only matches keys exactly and is never English. A
        single typed word can also be transliterated or, as a last resort, kept."""
        cached = self._choice_cache.get((typed, whole))
        if cached is None:
            if len(self._choice_cache) >= CHOICE_CACHE_SIZE:
                self._choice_cache.clear()
            cached = self._choice_cache[typed, whole] = self._choices(typed, whole)
        return cached

    def _choices(self, typed: str, whole: bool) -> list[Choice]:
        out = [
            Choice(word, emission, form.source, form.spelling)
            for word, (emission, form) in self.matcher.emissions(typed, fuzzy_keys=whole).items()
        ]
        if whole and typed.lower() in self.english:
            out.append(Choice(typed, 0.0, "english", typed.lower()))
        if whole and " " not in typed:
            guess = self.transliterator.transliterate(typed)
            if guess and guess not in {c.text for c in out}:
                out.append(Choice(guess, FALLBACK_EMISSION, "fallback", typed.lower()))
            out.append(Choice(typed, TYPED_EMISSION, "typed", typed))
        return self._with_picks(typed, out) if whole else out

    def _with_picks(self, typed: str, choices: list[Choice]) -> list[Choice]:
        picks = self.user.picks(typed)
        if not picks:
            return choices
        out = []
        for choice in choices:
            if choice.text in picks:
                bonus = LEARNED_WEIGHT * math.log1p(picks[choice.text])
                choice = Choice(
                    choice.text, choice.emission + bonus, choice.source, choice.spelling
                )
            out.append(choice)
        offered = {c.text for c in out}
        for word, count in picks.items():
            if word not in offered:
                bonus = LEARNED_WEIGHT * math.log1p(count)
                if word not in self.lexicon:
                    bonus += LEARNED_UNKNOWN_BONUS
                out.append(Choice(word, bonus, "learned", typed.lower()))
        return out

    def learn(self, typed: str, word: str) -> None:
        """Record that the user picked `word` for `typed`, so it ranks higher next time."""
        self.user.learn(typed, word)
        self._choice_cache.clear()

    def suggest(self, text: str, n: int = 5) -> list[Suggestion]:
        """Ranked readings of the last word of `text`, in the context of the words before
        it. While the last word is still being typed (no space or punctuation after it),
        words it could be the start of are suggested too."""
        tokens = self.decoder.convert(text, n).tokens
        if not tokens:
            return []
        last = tokens[-1]
        before = tokens[-2].choices[0] if len(tokens) > 1 else None
        previous = before.text if before and before.is_khmer else None
        candidates = list(last.choices)
        if last.end == len(text):
            for word, (emission, form) in self.matcher.completions(last.typed).items():
                candidates.append(Choice(word, emission, "completion", form.spelling))
        best: dict[str, Suggestion] = {}
        for choice in candidates:
            score = choice.emission + self.decoder.language_model(previous, choice)
            if choice.text not in best or score > best[choice.text].score:
                best[choice.text] = Suggestion(
                    choice.text, score, last.start, last.end, choice.source
                )
        return sorted(best.values(), key=lambda s: -s.score)[:n]

    @cached_property
    def romanizer(self) -> Romanizer:
        return Romanizer(self.lexicon)

    def romanize(self, khmer: str, style: Style = "chat") -> str:
        """Romanize Khmer text: "chat" spells words the way people type them, "ungegn"
        follows the UNGEGN standard."""
        return self.romanizer.romanize(khmer, style)

    def analyze(self, text: str, n: int = 5) -> Conversion:
        """The best conversion, the n best alternatives, and ranked choices per span."""
        return self.decoder.convert(text, n)

    def convert(self, text: str) -> str:
        """The best Khmer conversion of romanized `text`."""
        return self.decoder.convert(text, 1).text
