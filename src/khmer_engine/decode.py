"""Convert romanized text to Khmer with a Viterbi search over word sequences.

The input is split into phrases: runs of Latin words separated only by spaces. Each
phrase is decoded on its own; punctuation, digits, line breaks and Khmer script between
phrases are copied through unchanged.

Inside a phrase, a word may be typed across several Latin words ("or kun" for អរគុណ),
so a span covers one to three of them. Several words may also be typed as one
("soksabayte"), so a span can be a piece of a typed word; pieces only match keys
exactly and pay a cost for each split. Every span offers some choices (from the
`choices` callback), and the search picks the sequence with the best total of
emission scores (how well each choice fits its typed letters) and bigram language
model scores (how likely each word is after the one before). Keeping several
hypotheses per position gives the n best conversions as well.
"""

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from khmer_engine.lexicon import Lexicon

# Latin letters, including the diacritics of UNGEGN romanization, and apostrophes.
_LATIN = "A-Za-z\u00c0-\u024f'\u2019"
_TOKENS = re.compile(rf"(?P<word>[{_LATIN}]+)|(?P<space>[^\S\n]+)|(?P<other>.)", re.S)


@dataclass(frozen=True)
class Choice:
    """One reading of a span of typed text. "english" and "typed" choices keep the
    typed text; every other source is Khmer."""

    text: str
    emission: float
    source: str
    spelling: str = ""

    @property
    def is_khmer(self) -> bool:
        return self.source not in ("english", "typed")


@dataclass(frozen=True)
class Token:
    """A span of the input and its ranked readings; `choices[0]` is the one used."""

    typed: str
    start: int  # character offsets in the input, so a caller can replace the span
    end: int
    choices: list[Choice]


@dataclass(frozen=True)
class Conversion:
    text: str
    tokens: list[Token]  # one per converted span, in order
    alternatives: list[str]  # the n best conversions of the whole input, best first


@dataclass(frozen=True)
class Settings:
    """Search parameters. Tuned on eval/testset.tsv."""

    language_model: float = 0.7  # weight of the bigram log probability
    english: float = 7.0  # cost of keeping a word in English, about a mid-frequency word
    join: float = 1.0  # cost per space inside a span ("or kun")
    split: float = 1.0  # cost per split inside a typed word ("soksabay|te")
    max_words_per_span: int = 3
    min_split_length: int = 4  # shorter typed words are never split
    max_piece_length: int = 12
    choices_per_span: int = 8
    beam: int = 8


# Called with the typed text of a span (several typed words keep their spaces), and
# whether the span is made of whole typed words (True) or is a piece of one (False);
# pieces should only match exactly.
ChoiceSource = Callable[[str, bool], list[Choice]]


@dataclass
class _Hypothesis:
    score: float
    previous: str | None  # last Khmer word, for the bigram
    back: "_Hypothesis | None" = None
    span: tuple[int, int] = (0, 0)  # letter positions in the phrase
    choice: Choice | None = None

    def path(self) -> list["_Hypothesis"]:
        out = []
        node: _Hypothesis | None = self
        while node is not None and node.choice is not None:
            out.append(node)
            node = node.back
        out.reverse()
        return out


@dataclass
class _Phrase:
    """Typed words separated by spaces. Positions count letters, ignoring the spaces."""

    words: list[tuple[str, int, int]] = field(default_factory=list)  # (text, start, end)

    def offsets(self) -> list[int]:
        """The position where each word starts, then the end of the phrase."""
        out = [0]
        for text, _, _ in self.words:
            out.append(out[-1] + len(text))
        return out

    def typed(self, start: int, end: int) -> str:
        """The typed text between two positions, with the spaces between words."""
        pieces = []
        for (text, _, _), offset in zip(self.words, self.offsets(), strict=False):
            piece = text[max(start - offset, 0) : max(end - offset, 0)]
            if piece:
                pieces.append(piece)
        return " ".join(pieces)

    def characters(self, start: int, end: int) -> tuple[int, int]:
        """Character offsets in the input of the text between two positions."""
        offsets = self.offsets()
        first = max(i for i, o in enumerate(offsets[:-1]) if o <= start)
        last = max(i for i, o in enumerate(offsets[:-1]) if o < end)
        return (
            self.words[first][1] + start - offsets[first],
            self.words[last][1] + end - offsets[last],
        )


def _segments(text: str) -> Iterator[str | _Phrase]:
    """Split input into phrases and the text between them."""
    phrase = _Phrase()
    pending_space = ""
    for match in _TOKENS.finditer(text):
        kind = match.lastgroup
        if kind == "word":
            phrase.words.append((match.group(), match.start(), match.end()))
            pending_space = ""
        elif kind == "space" and phrase.words:
            pending_space = match.group()
        else:
            if phrase.words:
                yield phrase
                phrase = _Phrase()
            if pending_space:
                yield pending_space
                pending_space = ""
            yield match.group()
    if phrase.words:
        yield phrase
    if pending_space:
        yield pending_space


def join(choices: list[Choice]) -> str:
    """Khmer words are written together; English words get a space on each side."""
    out = ""
    for i, choice in enumerate(choices):
        if i and (not choice.is_khmer or not choices[i - 1].is_khmer):
            out += " "
        out += choice.text
    return out


class Decoder:
    def __init__(self, lexicon: Lexicon, choices: ChoiceSource, settings: Settings | None = None):
        self.lexicon = lexicon
        self.choices = choices
        self.settings = settings or Settings()

    def _language_model(self, previous: str | None, choice: Choice) -> float:
        if not choice.is_khmer:
            return -self.settings.english
        if previous is None:
            score = self.lexicon.logprob(choice.text)
        else:
            score = self.lexicon.bigram_logprob(previous, choice.text)
        return self.settings.language_model * score

    def _ranked(self, typed: str, whole: bool) -> list[Choice]:
        """The span's best choices without context, so the search only weighs those."""
        ranked = sorted(
            self.choices(typed, whole),
            key=lambda c: -(c.emission + self._language_model(None, c)),
        )
        return ranked[: self.settings.choices_per_span]

    def _spans(self, phrase: _Phrase) -> dict[tuple[int, int], tuple[list[Choice], float]]:
        """Every span with its choices and its cost."""
        settings = self.settings
        offsets = phrase.offsets()
        n = len(phrase.words)
        out = {}
        for i in range(n):
            for j in range(i + 1, min(i + settings.max_words_per_span, n) + 1):
                typed = " ".join(w[0] for w in phrase.words[i:j])
                out[offsets[i], offsets[j]] = (
                    self._ranked(typed, True),
                    settings.join * (j - i - 1),
                )
        for i, (word, _, _) in enumerate(phrase.words):
            if len(word) < settings.min_split_length:
                continue
            for a in range(len(word)):
                for b in range(a + 2, min(a + settings.max_piece_length, len(word)) + 1):
                    if a == 0 and b == len(word):
                        continue  # the whole word is above
                    # Charge each split once, on the piece that ends inside the word.
                    cost = settings.split if b < len(word) else 0.0
                    out[offsets[i] + a, offsets[i] + b] = (self._ranked(word[a:b], False), cost)
        return {span: value for span, value in out.items() if value[0]}

    def _search(self, phrase: _Phrase) -> tuple[list[_Hypothesis], dict]:
        spans = self._spans(phrase)
        starting: dict[int, list[tuple[int, list[Choice], float]]] = {}
        for (start, end), (choices, cost) in spans.items():
            starting.setdefault(start, []).append((end, choices, cost))
        length = phrase.offsets()[-1]
        beams: dict[int, list[_Hypothesis]] = {0: [_Hypothesis(0.0, None)]}
        for position in range(length):
            for end, choices, cost in starting.get(position, ()):
                for hypothesis in beams.get(position, ()):
                    for choice in choices:
                        score = hypothesis.score + choice.emission - cost
                        score += self._language_model(hypothesis.previous, choice)
                        previous = choice.text if choice.is_khmer else None
                        new = _Hypothesis(score, previous, hypothesis, (position, end), choice)
                        self._add(beams, end, new)
        return beams.get(length, []), spans

    def _add(self, beams: dict[int, list[_Hypothesis]], position: int, new: _Hypothesis) -> None:
        beam = beams.setdefault(position, [])
        for i, old in enumerate(beam):
            if old.previous == new.previous:  # same context from here on: keep the better
                if new.score > old.score:
                    beam[i] = new
                    beam.sort(key=lambda h: -h.score)
                return
        beam.append(new)
        beam.sort(key=lambda h: -h.score)
        del beam[self.settings.beam :]

    def _tokens(self, phrase: _Phrase, best: _Hypothesis, spans: dict, n: int) -> list[Token]:
        tokens = []
        previous = None
        for step in best.path():
            start, end = step.span
            assert step.choice is not None
            others = sorted(
                (c for c in spans[start, end][0] if c != step.choice),
                key=lambda c: -(c.emission + self._language_model(previous, c)),
            )
            first, last = phrase.characters(start, end)
            choices = [step.choice, *others][:n]
            tokens.append(Token(phrase.typed(start, end), first, last, choices))
            previous = step.previous
        return tokens

    def convert(self, text: str, n: int = 5) -> Conversion:
        """Convert `text`, keeping the n best readings of each span and of the whole."""
        pieces: list[list[str]] = [[]]  # alternatives of each piece of output, in order
        tokens: list[Token] = []
        for segment in _segments(text):
            if isinstance(segment, str):
                pieces.append([segment])
                continue
            finals, spans = self._search(segment)
            if not finals:  # nothing matched: keep the typed text
                pieces.append([" ".join(w[0] for w in segment.words)])
                continue
            readings = list(dict.fromkeys(join([h.choice for h in f.path()]) for f in finals))
            pieces.append(readings[:n])
            tokens.extend(self._tokens(segment, finals[0], spans, n))
        pieces = [p for p in pieces if p]
        best = "".join(p[0] for p in pieces)
        # Alternatives change one phrase at a time, keeping the best reading elsewhere.
        alternatives = [best]
        for i, options in enumerate(pieces):
            for option in options[1:]:
                firsts = [p[0] for p in pieces]
                firsts[i] = option
                alternatives.append("".join(firsts))
        return Conversion(best, tokens, alternatives[:n])
