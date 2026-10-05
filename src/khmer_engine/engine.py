"""The conversion engine: lexicon, matcher and decoder together."""

from khmer_engine.decode import Choice, Conversion, Decoder, Settings
from khmer_engine.lexicon import Lexicon
from khmer_engine.match import Matcher, Weights, read_chat_spellings


class Engine:
    """Converts romanized Khmer to Khmer script.

    By default it uses the sample lexicon shipped with the package and the curated chat
    spellings. Pass `Lexicon.load("data/build")` for the full lexicon.
    """

    def __init__(
        self,
        lexicon: Lexicon | None = None,
        *,
        chat_spellings: list[tuple[str, str]] | None = None,
        weights: Weights | None = None,
        settings: Settings | None = None,
    ):
        self.lexicon = lexicon or Lexicon.sample()
        spellings = read_chat_spellings() if chat_spellings is None else chat_spellings
        self.matcher = Matcher(self.lexicon, spellings, weights)
        self.decoder = Decoder(self.lexicon, self.choices, settings)

    def choices(self, typed: str) -> list[Choice]:
        """Every reading of one span of typed text, with its emission score."""
        return [
            Choice(word, emission, form.source, form.spelling)
            for word, (emission, form) in self.matcher.emissions(typed).items()
        ]

    def analyze(self, text: str, n: int = 5) -> Conversion:
        """The best conversion, the n best alternatives, and ranked choices per span."""
        return self.decoder.convert(text, n)

    def convert(self, text: str) -> str:
        """The best Khmer conversion of romanized `text`."""
        return self.decoder.convert(text, 1).text
