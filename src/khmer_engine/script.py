"""Khmer character classes (Unicode block U+1780-U+17FF).

Series assignments follow the UNGEGN report on Khmer romanization (version 4.0, 2013),
table I: consonants romanized with "â" are a-series, those with "ô" are o-series.
"""

from typing import Literal

Series = Literal["a", "o"]

COENG = "\u17d2"
NIKAHIT = "\u17c6"  # ំ
REAHMUK = "\u17c7"  # ះ
YUUKALEAPINTU = "\u17c8"  # ៈ
MUUSIKATOAN = "\u17c9"  # ៉ moves an o-series consonant to the a-series
TRIISAP = "\u17ca"  # ៊ moves an a-series consonant to the o-series
BANTOC = "\u17cb"  # ់ shortens the vowel before a final consonant
ROBAT = "\u17cc"  # ៌
TOANDAKHIAT = "\u17cd"  # ៍ marks letters that are written but not pronounced
KAKABAT = "\u17ce"  # ៎
AHSDA = "\u17cf"  # ៏
SAMYOK_SANNYA = "\u17d0"  # ័
VIRIAM = "\u17d1"  # ៑
LEK_TOO = "\u17d7"  # ៗ repeats the word before it
ZWNJ = "\u200c"
ZWJ = "\u200d"
ZWSP = "\u200b"

A_SERIES = frozenset("កខចឆដឋណតថបផឝសហឡអ")
O_SERIES = frozenset("គឃងជឈញឌឍទធនពភមយរលវឞ")
CONSONANTS = A_SERIES | O_SERIES

# A subscript decides the series of the syllable unless it is one of these; then the
# base consonant decides (UNGEGN note 3).
SERIES_NEUTRAL_SUBSCRIPTS = frozenset("ងញណនមយរលវស")

INDEPENDENT_VOWELS = frozenset("ឣឤឥឦឧឨឩឪឫឬឭឮឯឰឱឲឳ")
DEPENDENT_VOWELS = frozenset("ាិីឹឺុូួើឿៀេែៃោៅ")
SHIFTERS = frozenset((MUUSIKATOAN, TRIISAP))

# Signs that carry or change the vowel of a syllable, so a cluster that has one is
# never a bare final consonant.
VOCALIC_SIGNS = frozenset((NIKAHIT, REAHMUK, YUUKALEAPINTU, SAMYOK_SANNYA, AHSDA, KAKABAT))
OTHER_SIGNS = frozenset((BANTOC, ROBAT, TOANDAKHIAT, VIRIAM, "\u17d3", "\u17dd"))
SIGNS = VOCALIC_SIGNS | OTHER_SIGNS

# Inherent vowel characters (U+17B4, U+17B5) and joiners carry no sound.
IGNORED = frozenset(("\u17b4", "\u17b5", ZWNJ, ZWJ))

DIGITS = frozenset("០១២៣៤៥៦៧៨៩")


def series(consonant: str) -> Series:
    """Return the series of a consonant letter."""
    if consonant in A_SERIES:
        return "a"
    if consonant in O_SERIES:
        return "o"
    raise ValueError(f"not a Khmer consonant: {consonant!r}")


def is_khmer_letter(ch: str) -> bool:
    """Is `ch` part of a Khmer word (a letter, vowel sign, sign, coeng or joiner)?"""
    return (
        ch in CONSONANTS
        or ch in INDEPENDENT_VOWELS
        or ch in DEPENDENT_VOWELS
        or ch in SHIFTERS
        or ch in SIGNS
        or ch in IGNORED
        or ch == COENG
    )
