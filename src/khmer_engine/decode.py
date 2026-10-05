"""Convert romanized text to Khmer with a Viterbi search over word sequences.

The input is split into phrases: runs of Latin words separated only by spaces. Each
phrase is decoded on its own; punctuation, digits, line breaks and Khmer script between
phrases are copied through unchanged.

Inside a phrase, a word may be typed across several Latin words ("or kun" for អរគុណ),
so a span covers one to three of them. Every span offers some choices (from the
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
    """One reading of a span of typed text. Khmer choices are lexicon words unless
    `source` says otherwise; "english" choices keep the typed text."""

    text: str
    emission: float
    source: str
    spelling: str = ""

    @property
    def is_khmer(self) -> bool:
        return self.source != "english"


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
    join: float = 1.0  # cost per space inside a span ("or kun")
    max_words_per_span: int = 3
    choices_per_span: int = 8
    beam: int = 8


ChoiceSource = Callable[[str], list[Choice]]


@dataclass
class _Hypothesis:
    score: float
    previous: str | None  # last Khmer word, for the bigram
    back: "_Hypothesis | None" = None
    span: tuple[int, int] = (0, 0)  # word indexes in the phrase
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
    words: list[tuple[str, int, int]] = field(default_factory=list)  # (text, start, end)


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
            return 0.0
        if previous is None:
            score = self.lexicon.logprob(choice.text)
        else:
            score = self.lexicon.bigram_logprob(previous, choice.text)
        return self.settings.language_model * score

    def _spans(self, phrase: _Phrase) -> dict[tuple[int, int], list[Choice]]:
        out = {}
        n = len(phrase.words)
        for start in range(n):
            for end in range(start + 1, min(start + self.settings.max_words_per_span, n) + 1):
                typed = "".join(w[0] for w in phrase.words[start:end])
                ranked = sorted(self.choices(typed), key=lambda c: -c.emission)
                if ranked:
                    out[start, end] = ranked[: self.settings.choices_per_span]
        return out

    def _search(self, phrase: _Phrase) -> tuple[list[_Hypothesis], dict]:
        spans = self._spans(phrase)
        n = len(phrase.words)
        beams: dict[int, list[_Hypothesis]] = {0: [_Hypothesis(0.0, None)]}
        for position in range(n):
            for (start, end), choices in spans.items():
                if start != position or position not in beams:
                    continue
                cost = self.settings.join * (end - start - 1)
                for hypothesis in beams[position]:
                    for choice in choices:
                        score = hypothesis.score + choice.emission - cost
                        score += self._language_model(hypothesis.previous, choice)
                        previous = choice.text if choice.is_khmer else None
                        new = _Hypothesis(score, previous, hypothesis, (start, end), choice)
                        self._add(beams, end, new)
        return beams.get(n, []), spans

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
                (c for c in spans[start, end] if c != step.choice),
                key=lambda c: -(c.emission + self._language_model(previous, c)),
            )
            words = phrase.words[start:end]
            typed = " ".join(w[0] for w in words)
            tokens.append(Token(typed, words[0][1], words[-1][2], [step.choice, *others][:n]))
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
