"""Matching keys for romanized Khmer.

People spell the same Khmer word many ways in Latin letters: "sous dey", "suosdey",
"sursdey"; "chong", "jong"; "orkun", "okun". `key` maps a spelling to a coarse form in
which the common variants coincide, so looking a word up by its key finds it however
it was typed. The variants folded are:

- consonants: c/ch/j, chh, k/kh/g/gh/q, ph/p, th/t, w/v, nh/ny, x/s
- vowel spellings that chat uses for one sound (see `VOWELS`): o/ou/u/ao, e/ae/eu/i,
  ea/ia/ie
- a final i after another vowel, which is the glide y: "sabai" is "sabay"
- r after a vowel, which chat uses to lengthen it: "orkun", "khmer"
- h or s at the end of a word, which are both pronounced h: "preah", "pros"
- doubled letters: "sabbay"
- diacritics and apostrophes, so UNGEGN spellings match too: "Kâmpŭchéa", "l'â"

Keys are lowercase consonants and uppercase vowel groups. They are only for lookup;
candidates are then ranked against the exact spelling.
"""

import re
import unicodedata

# Letter units, longest first.
_UNITS = re.compile("chh|ch|kh|gh|ng|nh|ny|ph|th|[a-z]")

CONSONANTS = {
    "b": "b", "c": "c", "ch": "c", "chh": "c", "j": "c", "d": "d", "f": "f",
    "g": "k", "gh": "k", "k": "k", "kh": "k", "q": "k", "h": "h", "l": "l",
    "m": "m", "n": "n", "ng": "N", "nh": "Y", "ny": "Y", "p": "p", "ph": "p",
    "r": "r", "s": "s", "x": "s", "t": "t", "th": "t", "v": "v", "w": "v",
    "y": "y", "z": "z",
}  # fmt: skip

# Vowel spellings grouped by how chat uses them. A run of vowel letters that is not
# listed is keyed letter by letter.
VOWELS = {
    "a": "A", "aa": "A",
    # Back vowels, and ោ/ៅ, which chat writes as o as often as ao: កោះកុង "Koh Kong".
    "o": "O", "oo": "O", "ou": "O", "u": "O", "uu": "O", "uo": "O", "ua": "O", "uoa": "O",
    "ao": "O", "au": "O",
    # Front and central vowels. Chat writes ɨ and ə as e, eu or i: ដឹង "deng",
    # មិន "min" or "men", ពិត "pit".
    "e": "E", "ee": "E", "ae": "E", "eae": "E", "i": "E", "ii": "E",
    "eu": "E", "oe": "E", "ue": "E", "oeu": "E", "ueu": "E", "aeu": "E", "oea": "E",
    "ea": "J", "ia": "J", "ie": "J", "iea": "J", "eia": "J",
    "oa": "Q",
}  # fmt: skip

_VOWEL_LETTERS = frozenset("aeiou")
_VOWEL_KEYS = frozenset(VOWELS.values())
_FINAL_H = frozenset("hs")


def fold(text: str) -> str:
    """Lowercase ASCII letters only: no diacritics, apostrophes, spaces or digits."""
    decomposed = unicodedata.normalize("NFD", text.lower().replace("œ", "oe").replace("æ", "ae"))
    return "".join(ch for ch in decomposed if "a" <= ch <= "z")


def _vowel_run(run: str) -> list[str]:
    glide = len(run) > 1 and run.endswith("i") and not run.endswith("ii")
    if glide:
        run = run[:-1]
    out = [VOWELS[run]] if run in VOWELS else [VOWELS[ch] for ch in run]
    if glide:
        out.append("y")
    return out


def consonants(spelling: str) -> str | None:
    """The consonant letters of a romanization, the way chat abbreviates a common word:
    "tov" is "tv" and "deng" is "dg", since chat writes ng as g at the end of an
    abbreviation. None if fewer than two consonants are left, as a single letter could
    stand for too many words."""
    units = [unit for unit in _UNITS.findall(fold(spelling)) if unit not in _VOWEL_LETTERS]
    if len(units) < 2:
        return None
    return "".join("g" if unit == "ng" else unit for unit in units)


def key(text: str, final: bool = True) -> str:
    """The matching key of a romanized spelling. With `final` false the text is taken
    to continue (a syllable inside a word, or a word still being typed), so the rules
    for the end of a word (dropping a last r, h or s) do not apply."""
    units = _UNITS.findall(fold(text))
    symbols: list[str] = []
    i = 0
    while i < len(units):
        if units[i] in _VOWEL_LETTERS:
            j = i
            while j < len(units) and units[j] in _VOWEL_LETTERS:
                j += 1
            symbols.extend(_vowel_run("".join(units[i:j])))
            i = j
        else:
            symbols.append(CONSONANTS[units[i]])
            i += 1
    out: list[str] = []
    for i, symbol in enumerate(symbols):
        after_vowel = bool(out) and out[-1] in _VOWEL_KEYS
        next_is_vowel = i + 1 < len(symbols) and symbols[i + 1] in _VOWEL_KEYS
        word_end = final and i == len(symbols) - 1
        text_end = i == len(symbols) - 1
        if symbol == "r" and after_vowel and not next_is_vowel and (word_end or not text_end):
            continue  # orkun, khmer
        if symbol in _FINAL_H and after_vowel and word_end:
            continue  # preah, pros
        if out and out[-1] == symbol:
            continue  # sabbay
        out.append(symbol)
    return "".join(out)
