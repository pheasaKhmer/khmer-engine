"""Turn phonemic transcriptions into chat-style Latin spellings.

The transcriptions follow Google's Khmer pronunciation lexicon: phones separated by
spaces and syllables by " . ", for example "s o k . s a p . ɓ aa j" for សុខសប្បាយ.
Chat spellings follow the sound, so they come out close to what people type ("sok",
"mean", "touch", "srey") even where the spelling suggests otherwise.
"""

ONSETS = {
    "ʔ": "", "k": "k", "kh": "kh", "c": "ch", "ch": "chh", "ŋ": "ng", "ɲ": "nh",
    "ɗ": "d", "t": "t", "th": "th", "n": "n", "ɓ": "b", "p": "p", "ph": "ph",
    "m": "m", "j": "y", "r": "r", "l": "l", "w": "v", "s": "s", "h": "h",
    "f": "f", "g": "g", "z": "z",
}  # fmt: skip

CODAS = {
    "ʔ": "", "k": "k", "c": "ch", "ŋ": "ng", "ɲ": "nh", "t": "t", "n": "n",
    "p": "p", "m": "m", "j": "y", "r": "r", "l": "l", "w": "v", "s": "s",
    "h": "h", "f": "f",
    # Only in loanwords.
    "ch": "ch", "kh": "k", "ɓ": "b", "ɗ": "d", "g": "g", "z": "z",
}  # fmt: skip

VOWELS = {
    "a": "a", "aa": "a", "ɑ": "o", "ɑɑ": "o", "ɔ": "o", "ɔɔ": "o",
    "o": "o", "oo": "ou", "u": "u", "uu": "u",
    "ə": "e", "əə": "eu", "e": "e", "ee": "e", "ɛ": "e", "ɛɛ": "ae",
    "i": "i", "ii": "i", "ɨ": "eu", "ɨɨ": "eu",
    "ie": "ea", "iə": "ie", "ea": "ea", "oa": "oa", "uə": "uo", "ɨə": "eu",
    "ɛə": "ea", "ae": "ae", "aə": "aeu", "ao": "ao",
}  # fmt: skip

# Long ɑ and ɔ without a coda are typed with an r: អរគុណ "orkun", ល្អ "lor".
OPEN_VOWELS = {"ɑɑ": "or", "ɔɔ": "or"}

# Rimes typed differently from the sum of their parts: ទៅ is "tov", not "teuv".
RIMES = {("ɨ", "w"): "ov", ("ɨɨ", "w"): "ov"}

# A doubled consonant is typed once: សប្បាយ is "sabay", not "sapbay", and ចិត្ត is
# "cheto". These are a coda and the next onset that Khmer writes as one letter twice
# (ប final is pronounced p). Other pairs keep both letters: បាត់ដំបង is "Battambang".
_DOUBLED = {("p", "ɓ")}

SILENCES = frozenset(("sil", "pau"))


def _syllable(phones: list[str], next_onset: str = "") -> str:
    vowel_at = next((i for i, p in enumerate(phones) if p in VOWELS), None)
    if vowel_at is None:
        return "".join(ONSETS[p] for p in phones)
    onset, vowel, coda = phones[:vowel_at], phones[vowel_at], phones[vowel_at + 1 :]
    out = "".join(ONSETS[p] for p in onset)
    if (vowel, *coda) in RIMES:
        return out + RIMES[(vowel, *coda)]
    if not coda and vowel in OPEN_VOWELS:
        return out + OPEN_VOWELS[vowel]
    if coda and (coda[-1] == next_onset or (coda[-1], next_onset) in _DOUBLED):
        coda = coda[:-1]
    return out + VOWELS[vowel] + "".join(CODAS[p] for p in coda)


def to_chat(transcription: str) -> str:
    """Chat-style Latin spelling of a phonemic transcription."""
    syllables = [
        [p for p in syllable.split() if p not in SILENCES]
        for syllable in transcription.split(" . ")
    ]
    out = []
    for i, phones in enumerate(syllables):
        following = syllables[i + 1][0] if i + 1 < len(syllables) and syllables[i + 1] else ""
        try:
            out.append(_syllable(phones, following))
        except KeyError as error:
            raise ValueError(f"unknown phone {error.args[0]!r} in {transcription!r}") from None
    return "".join(out)
