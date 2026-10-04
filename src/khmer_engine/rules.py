"""Rule-based romanization of Khmer, from the spelling alone.

Two styles:

- "ungegn" follows the UNGEGN report on Khmer romanization (version 4.0, September 2013,
  https://www.eki.ee/wgrs/rom1_km.pdf). Table and note numbers in comments refer to it.
- "chat" follows the Geographic Department system Cambodia has used since 1997 (the
  report's "Other systems of romanization", and Wikipedia's tables for the gaps): the
  same consonants without apostrophes, and vowels without diacritics. It is the closest
  standard to how people type Khmer in Latin letters.
"""

from typing import Literal

from khmer_engine import script
from khmer_engine.syllables import Syllable, syllables

Style = Literal["ungegn", "chat"]

# Tables I and II. Initial and final consonants use the same letters.
_CONSONANTS = {
    "ក": "k", "ខ": "kh", "គ": "k", "ឃ": "kh", "ង": "ng",
    "ច": "ch", "ឆ": "chh", "ជ": "ch", "ឈ": "chh", "ញ": "nh",
    "ដ": "d", "ឋ": "th", "ឌ": "d", "ឍ": "th", "ណ": "n",
    "ត": "t", "ថ": "th", "ទ": "t", "ធ": "th", "ន": "n",
    "ប": "b", "ផ": "ph", "ព": "p", "ភ": "ph", "ម": "m",
    "យ": "y", "រ": "r", "ល": "l", "វ": "v",
    "ឝ": "s", "ឞ": "s",  # obsolete, not in the tables
    "ស": "s", "ហ": "h", "ឡ": "l", "អ": "'",
}  # fmt: skip

_BREVE = "\u0306"
_OE_SHORT = "œ" + _BREVE

# Tables IV and V, as (a-series, o-series). Keys are the dependent vowel, optionally
# followed by nikahit or reahmuk, or one of the named combinations below. Where the
# o-series value depends on the final consonant, it is "oă|eă" (note 6).
_INHERENT = ""
_INHERENT_BANTOC = "bantoc"
_AA_BANTOC = "ា+bantoc"
_SAMYOK = "samyok"
_SAMYOK_Y = "samyok+y"
_AAM_NG = "ាំង"

_UNGEGN_NUCLEI: dict[str, tuple[str, str]] = {
    _INHERENT: ("â", "ô"),  # table I
    _INHERENT_BANTOC: ("á", "ó"),  # V.1
    "ា": ("a", "éa"),
    _AA_BANTOC: ("ă", "oă|eă"),  # V.2
    _SAMYOK: ("ă", "oă|eă"),  # V.3
    _SAMYOK_Y: ("ăy", "oăy"),  # not given; V.3 before y
    "ៈ": ("ă", "eă"),  # not given; Wikipedia's table
    "ិ": ("ĕ", "ĭ"),
    "ី": ("ei", "i"),
    "ឹ": (_OE_SHORT, _OE_SHORT),
    "ឺ": ("œ", "œ"),
    "ុ": ("ŏ", "ŭ"),
    "ូ": ("o", "u"),
    "ួ": ("uŏ", "uŏ"),
    "ើ": ("aeu", "eu"),
    "ឿ": ("œă", "œă"),
    "ៀ": ("iĕ", "iĕ"),
    "េ": ("é", "é"),
    "ែ": ("ê", "ê"),
    "ៃ": ("ai", "ey"),
    "ោ": ("aô", "oŭ"),
    "ៅ": ("au", "ŏu"),
    "ំ": ("âm", "um"),  # V.4
    "ុំ": ("om", "ŭm"),  # V.5
    "ាំ": ("ăm", "ŏâm"),  # V.6
    _AAM_NG: ("ăng", "eăng"),  # V.11
    "ះ": ("ăh", "eăh"),  # V.7
    "ុះ": ("ŏh", "ŭh"),  # V.8
    "េះ": ("éh", "éh"),  # V.9
    "ោះ": ("aôh", "ŏăh"),  # V.10
}

# Table III. ឧ may also be ŭ (note 10); ŏ is the default.
_UNGEGN_INDEPENDENT = {
    "ឣ": "â", "ឤ": "a", "ឥ": "ĕ", "ឦ": "ei", "ឧ": "ŏ", "ឨ": "ŏk", "ឩ": "o",
    "ឪ": "âu", "ឫ": "r" + _OE_SHORT, "ឬ": "rœ", "ឭ": "l" + _OE_SHORT, "ឮ": "lœ",
    "ឯ": "ê", "ឰ": "ai", "ឱ": "aô", "ឲ": "aô", "ឳ": "au",
}  # fmt: skip

# Geographic Department values. Two cells differ from that system to match how people
# type: ែ is "ae" in both series (the system has "eae" in the o-series) and ិះ is "ih"
# in the o-series (the system has "is").
_CHAT_NUCLEI: dict[str, tuple[str, str]] = {
    _INHERENT: ("a", "o"),
    _INHERENT_BANTOC: ("a", "o"),
    "ា": ("a", "ea"),
    _AA_BANTOC: ("a", "oa|ea"),
    _SAMYOK: ("a", "oa|ea"),
    _SAMYOK_Y: ("ai", "ey"),
    "ៈ": ("ak", "eak"),
    "ិ": ("e", "i"),
    "ី": ("ei", "i"),
    "ឹ": ("oe", "ue"),
    "ឺ": ("eu", "ueu"),
    "ុ": ("o", "u"),
    "ូ": ("ou", "u"),
    "ួ": ("uo", "uo"),
    "ើ": ("aeu", "eu"),
    "ឿ": ("oea", "oea"),
    "ៀ": ("ie", "ie"),
    "េ": ("e", "e"),
    "ែ": ("ae", "ae"),
    "ៃ": ("ai", "ey"),
    "ោ": ("ao", "ou"),
    "ៅ": ("au", "ov"),
    "ំ": ("am", "um"),
    "ុំ": ("om", "um"),
    "ាំ": ("am", "oam"),
    _AAM_NG: ("ang", "eang"),
    "ះ": ("ah", "eah"),
    "ិះ": ("eh", "ih"),
    "ុះ": ("oh", "uh"),
    "េះ": ("eh", "eh"),
    "ោះ": ("aoh", "uoh"),
}

_CHAT_INDEPENDENT = {
    "ឣ": "a", "ឤ": "a", "ឥ": "e", "ឦ": "ei", "ឧ": "o", "ឨ": "ok", "ឩ": "ou",
    "ឪ": "au", "ឫ": "rue", "ឬ": "rueu", "ឭ": "lue", "ឮ": "lueu",
    "ឯ": "ae", "ឰ": "ai", "ឱ": "ao", "ឲ": "ao", "ឳ": "au",
}  # fmt: skip

_NUCLEI = {"ungegn": _UNGEGN_NUCLEI, "chat": _CHAT_NUCLEI}
_INDEPENDENT = {"ungegn": _UNGEGN_INDEPENDENT, "chat": _CHAT_INDEPENDENT}

# Note 6: the o-series value is eă before these finals, otherwise oă.
_EA_FINALS = frozenset(("k", "kh", "ng", "h"))


def _nucleus_key(syllable: Syllable) -> tuple[str, int]:
    """The table key for a syllable's nucleus, and how many finals the key already spells."""
    vowel, signs, finals = syllable.vowel, syllable.signs, syllable.finals
    if script.SAMYOK_SANNYA in signs:
        if finals[:1] == ("យ",):
            return _SAMYOK_Y, 1
        return _SAMYOK, 0
    if script.NIKAHIT in signs:
        if vowel == "ា" and finals[:1] == ("ង",):
            return _AAM_NG, 1
        return vowel + script.NIKAHIT, 0
    if script.REAHMUK in signs:
        return vowel + script.REAHMUK, 0
    if script.YUUKALEAPINTU in signs:
        return script.YUUKALEAPINTU, 0
    if syllable.bantoc and finals:
        if vowel == "ា":
            return _AA_BANTOC, 0
        if not vowel:
            return _INHERENT_BANTOC, 0
    return vowel, 0


def _vowel(syllable: Syllable, final_letters: list[str], style: Style) -> tuple[str, int]:
    """Romanize the nucleus. Returns the text and how many finals it already spells."""
    nuclei = _NUCLEI[style]
    column = 0 if syllable.series == "a" else 1
    key, spelled = _nucleus_key(syllable)
    if key in nuclei:
        value = nuclei[key][column]
    else:
        # Combinations the tables leave out (ិះ, ើះ, ...): the vowel, then m or h.
        value = "".join(nuclei[v][column] for v in syllable.vowel)
        if script.NIKAHIT in syllable.signs:
            value += "m"
        if script.REAHMUK in syllable.signs:
            value += "h"
    if "|" in value:
        before_others, before_k_ng_h = value.split("|")
        k_ng_h = bool(final_letters) and final_letters[0] in _EA_FINALS
        value = before_k_ng_h if k_ng_h else before_others
    return value, spelled


def _subscript_ta(onset: tuple[str, ...], index: int, previous: Syllable | None) -> str:
    """Note 3: a subscript ត usually stands for ដ (d), except in ន្ត and before ្រ."""
    before_ro = onset[index + 1 : index + 2] == ("រ",)
    after_no = index == 0 and previous is not None and previous.finals[-1:] == ("ន",)
    return "t" if before_ro or after_no else "d"


def _consonant(letter: str, style: Style) -> str:
    if letter == "អ" and style == "chat":
        return ""
    return _CONSONANTS[letter]


def _onset(syllable: Syllable, previous: Syllable | None, style: Style) -> str:
    out = []
    for i, letter in enumerate(syllable.onset):
        written_below = i > 0 or syllable.subscript_onset
        if (
            letter == "ប"
            and not written_below
            and (len(syllable.onset) > 1 or syllable.shifter == script.MUUSIKATOAN)
        ):
            out.append("p")  # note 4
        elif letter == "ត" and written_below:
            out.append(_subscript_ta(syllable.onset, i, previous))
        elif letter == "អ" and previous is None and syllable.onset == ("អ",) and syllable.vowel:
            pass  # note 5: word-initial ' before a vowel is omitted
        elif letter in script.INDEPENDENT_VOWELS:
            out.append(_INDEPENDENT[style][letter])  # written as a subscript: ហ្ឫទ័យ
        else:
            out.append(_consonant(letter, style))
    return "".join(out)


def _syllable(syllable: Syllable, previous: Syllable | None, style: Style) -> str:
    if style == "chat" and syllable.silent:
        return ""  # toandakhiat: written, not pronounced
    silent_finals = style == "chat" and syllable.silent_finals
    finals = [] if silent_finals else [_consonant(f, style) for f in syllable.finals]
    if syllable.independent:
        head = _INDEPENDENT[style][syllable.independent]
        spelled = 0
    else:
        vowel, spelled = _vowel(syllable, finals, style)
        if not syllable.vowel and set(syllable.onset) & script.INDEPENDENT_VOWELS:
            vowel = ""  # the subscript independent vowel is the nucleus
        head = _onset(syllable, previous, style) + vowel
    robat = "r" if syllable.robat else ""  # note 7
    return head + robat + "".join(finals[spelled:])


def romanize_syllables(parts: list[Syllable], style: Style = "ungegn") -> str:
    """Romanize a word given as syllables."""
    out = []
    previous = None
    for syllable in parts:
        out.append(_syllable(syllable, previous, style))
        previous = syllable
    return "".join(out)


def romanize_word(word: str, style: Style = "ungegn") -> str:
    """Romanize one Khmer word from its spelling."""
    return romanize_syllables(syllables(word), style)
