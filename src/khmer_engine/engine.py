"""The conversion engine: lexicon, matcher and decoder together."""

from khmer_engine.decode import Choice, Conversion, Decoder, Settings
from khmer_engine.english import read_english
from khmer_engine.lexicon import Lexicon
from khmer_engine.match import Matcher, Weights, read_chat_spellings
from khmer_engine.transliterate import Transliterator

# Emission of a syllable-by-syllable transliteration: it is a guess, so any reasonable
# lexicon reading should beat it.
FALLBACK_EMISSION = -8.0
# Emission of keeping a typed word as it is, when nothing else reads it.
TYPED_EMISSION = -20.0


class Engine:
    """Converts romanized Khmer to Khmer script.

    By default it uses the sample lexicon shipped with the package, the curated chat
    spellings and the English word list. Pass `Lexicon.load("data/build")` for the full
    lexicon.
    """

    def __init__(
        self,
        lexicon: Lexicon | None = None,
        *,
        chat_spellings: list[tuple[str, str]] | None = None,
        english: frozenset[str] | None = None,
        weights: Weights | None = None,
        settings: Settings | None = None,
    ):
        self.lexicon = lexicon or Lexicon.sample()
        spellings = read_chat_spellings() if chat_spellings is None else chat_spellings
        self.matcher = Matcher(self.lexicon, spellings, weights)
        self.english = read_english() if english is None else english
        self.transliterator = Transliterator.from_lexicon(self.lexicon)
        self.decoder = Decoder(self.lexicon, self.choices, settings)

    def choices(self, typed: str, whole: bool = True) -> list[Choice]:
        """Every reading of one span of typed text, with its emission score. A piece of a
        typed word (`whole` false) only matches keys exactly and is never English. A
        single typed word can also be transliterated or, as a last resort, kept."""
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
        return out

    def analyze(self, text: str, n: int = 5) -> Conversion:
        """The best conversion, the n best alternatives, and ranked choices per span."""
        return self.decoder.convert(text, n)

    def convert(self, text: str) -> str:
        """The best Khmer conversion of romanized `text`."""
        return self.decoder.convert(text, 1).text
