"""Split Khmer words into written clusters and spoken syllables.

A cluster is what Khmer writes as one unit: a base letter, its subscripts, a vowel and
signs. A syllable is what is pronounced. They differ because the final consonant of one
syllable is often written as the base of the next cluster, with the next onset written
under it: in កម្ពុជា the ម closes "kam" and the ព under it starts "pu".

Which reading is meant is not marked in the script, so `syllables` scores the possible
readings and keeps the cheapest. The costs encode a few preferences:

- a bare consonant closes the open syllable before it rather than starting its own
  syllable with an inherent vowel (កក is "kak", not "ka-ka");
- a doubled consonant such as ប្ប is split across two syllables (សប្បាយ is "sab-bay");
- a word does not end in a bare consonant with an inherent vowel (បេក្ខជន ends "chon").
"""

from dataclasses import dataclass, field
from enum import IntEnum

from pheasa import normalize

from khmer_engine import script


@dataclass(frozen=True)
class Cluster:
    """One written cluster. `base` is "" when vowel signs appear without a letter."""

    text: str
    base: str
    subscripts: tuple[str, ...] = ()
    shifter: str = ""
    vowel: str = ""
    signs: str = ""

    @property
    def is_independent_vowel(self) -> bool:
        return self.base in script.INDEPENDENT_VOWELS

    @property
    def has_nucleus(self) -> bool:
        """Does the cluster carry its own vowel (so it cannot be a bare final)?"""
        return (
            not self.base
            or self.is_independent_vowel
            or bool(self.vowel)
            or any(sign in script.VOCALIC_SIGNS for sign in self.signs)
            # ហ្ឫទ័យ: an independent vowel written as a subscript is the vowel.
            or any(sub in script.INDEPENDENT_VOWELS for sub in self.subscripts)
        )

    @property
    def must_be_final(self) -> bool:
        """Bantoc and viriam only sit on final consonants."""
        return script.BANTOC in self.signs or script.VIRIAM in self.signs


@dataclass
class _ClusterBuilder:
    text: str = ""
    base: str = ""
    subscripts: list[str] = field(default_factory=list)
    shifter: str = ""
    vowel: str = ""
    signs: str = ""

    def build(self) -> Cluster:
        return Cluster(
            self.text, self.base, tuple(self.subscripts), self.shifter, self.vowel, self.signs
        )


def clusters(text: str) -> list[Cluster]:
    """Split normalized Khmer text into clusters. Characters outside words are skipped."""
    out: list[Cluster] = []
    current: _ClusterBuilder | None = None
    after_coeng = False
    for ch in text:
        is_letter = ch in script.CONSONANTS or ch in script.INDEPENDENT_VOWELS
        if is_letter and after_coeng and current is not None:
            current.subscripts.append(ch)
            current.text += ch
            after_coeng = False
            continue
        after_coeng = False
        if is_letter:
            if current is not None:
                out.append(current.build())
            current = _ClusterBuilder(text=ch, base=ch)
            continue
        if not script.is_khmer_letter(ch):
            continue
        if current is None:
            current = _ClusterBuilder()
        current.text += ch
        if ch == script.COENG:
            after_coeng = True
        elif ch in script.SHIFTERS:
            current.shifter = ch
        elif ch in script.DEPENDENT_VOWELS:
            current.vowel += ch
        elif ch in script.SIGNS:
            current.signs += ch
    if current is not None:
        out.append(current.build())
    return out


@dataclass(frozen=True)
class Syllable:
    """One spoken syllable.

    `onset` holds the onset consonants in writing order and is empty when the syllable
    starts with an independent vowel (`independent`). `subscript_onset` is true when the
    onset is written under the previous syllable's final consonant. `signs` holds the
    signs of the nucleus plus bantoc when it sits on the final. `silent` marks a nucleus
    written with toandakhiat (not pronounced), `silent_finals` the same for the finals.
    """

    text: str
    onset: tuple[str, ...] = ()
    independent: str = ""
    shifter: str = ""
    vowel: str = ""
    signs: str = ""
    finals: tuple[str, ...] = ()
    subscript_onset: bool = False
    robat: bool = False
    silent: bool = False
    silent_finals: bool = False

    @property
    def bantoc(self) -> bool:
        return script.BANTOC in self.signs

    @property
    def series(self) -> script.Series:
        """Series of the nucleus: from the onset consonants and shifter (UNGEGN notes 2-3)."""
        if not self.onset:
            return "a"
        result = script.series(self.onset[0])
        subscript = self.onset[1] if len(self.onset) > 1 else ""
        if subscript in script.CONSONANTS and subscript not in script.SERIES_NEUTRAL_SUBSCRIPTS:
            result = script.series(subscript)
        if self.shifter == script.MUUSIKATOAN:
            return "a"
        if self.shifter == script.TRIISAP:
            return "o"
        return result


class _State(IntEnum):
    START = 0
    OPEN_INHERENT = 1  # bare onset, no final yet
    OPEN_VOWEL = 2  # explicit vowel, no final yet
    OPEN_AAM = 3  # ាំ, which can still take ង as a final (ាំង)
    CLOSED = 4


class _Action(IntEnum):
    # Order is the tie-break: earlier actions win when costs are equal.
    FINAL = 0  # the cluster is the final consonant(s) of the open syllable
    SPLIT = 1  # the base closes the open syllable; the subscripts start the next one
    ONSET = 2  # the cluster starts a new syllable


_OPEN = (_State.OPEN_INHERENT, _State.OPEN_VOWEL)
_LEFT_OPEN_COST = 1.0  # a syllable with an inherent vowel and no final
_WORD_END_OPEN_COST = 2.0  # the same at the end of a word
_SPLIT_AFTER_VOWEL_COST = 0.5  # សាស្ត្រ: prefer a new onset after an explicit vowel
_DOUBLED_ONSET_COST = 2.0  # ប្ប as an onset
_MISPLACED_FINAL_COST = 5.0  # bantoc on an onset


def _after_nucleus(cluster: Cluster) -> _State:
    if script.NIKAHIT in cluster.signs:
        return _State.OPEN_AAM if cluster.vowel == "ា" else _State.CLOSED
    if any(s in cluster.signs for s in (script.REAHMUK, script.YUUKALEAPINTU)):
        return _State.CLOSED
    if any(s in cluster.signs for s in (script.AHSDA, script.KAKABAT)):
        return _State.CLOSED
    return _State.OPEN_VOWEL


def _options(cluster: Cluster, state: _State, last: bool) -> list[tuple[_Action, float, _State]]:
    """Every legal reading of `cluster` after a syllable in `state`."""
    doubled = _DOUBLED_ONSET_COST if cluster.subscripts[:1] == (cluster.base,) else 0.0
    left_open = _LEFT_OPEN_COST if state == _State.OPEN_INHERENT else 0.0
    can_split = bool(cluster.subscripts) and state in _OPEN and not cluster.is_independent_vowel
    split_cost = 0.0 if state == _State.OPEN_INHERENT else _SPLIT_AFTER_VOWEL_COST
    out: list[tuple[_Action, float, _State]] = []
    if cluster.has_nucleus:
        if can_split:
            out.append((_Action.SPLIT, split_cost, _after_nucleus(cluster)))
        out.append((_Action.ONSET, doubled + left_open, _after_nucleus(cluster)))
        return out
    takes_final = state in _OPEN or (
        state == _State.OPEN_AAM and cluster.base == "ង" and not cluster.subscripts
    )
    if takes_final and (not cluster.subscripts or last):
        out.append((_Action.FINAL, 0.0, _State.CLOSED))
    if can_split:
        out.append((_Action.SPLIT, 0.0, _State.OPEN_INHERENT))
    misplaced = _MISPLACED_FINAL_COST if cluster.must_be_final else 0.0
    out.append((_Action.ONSET, doubled + left_open + misplaced, _State.OPEN_INHERENT))
    return out


def _best_actions(cs: list[Cluster]) -> list[_Action]:
    # Viterbi over (state, more than one syllable so far).
    Key = tuple[_State, bool]
    best: dict[Key, tuple[float, list[_Action]]] = {(_State.START, False): (0.0, [])}
    for i, cluster in enumerate(cs):
        last = i == len(cs) - 1
        nxt: dict[Key, tuple[float, list[_Action]]] = {}
        for (state, several), (cost, actions) in best.items():
            for action, step, new_state in _options(cluster, state, last):
                new_several = several or (action != _Action.FINAL and state != _State.START)
                key = (new_state, new_several)
                total = cost + step
                if key not in nxt or total < nxt[key][0]:
                    nxt[key] = (total, [*actions, action])
        best = nxt

    def final_cost(item: tuple[Key, tuple[float, list[_Action]]]) -> tuple[float, list[_Action]]:
        (state, several), (cost, actions) = item
        if state == _State.OPEN_INHERENT and several:
            cost += _WORD_END_OPEN_COST
        return cost, actions

    return min(map(final_cost, best.items()))[1]


@dataclass
class _SyllableBuilder:
    text: str = ""
    onset: tuple[str, ...] = ()
    independent: str = ""
    shifter: str = ""
    vowel: str = ""
    signs: str = ""
    finals: tuple[str, ...] = ()
    subscript_onset: bool = False
    robat: bool = False
    silent: bool = False
    silent_finals: bool = False

    def build(self) -> Syllable:
        return Syllable(**self.__dict__)


def _nucleus_signs(signs: str) -> str:
    return "".join(s for s in signs if s in script.VOCALIC_SIGNS)


def _start(cluster: Cluster, text: str, onset: tuple[str, ...], *, subscript: bool):
    independent = ""
    if cluster.is_independent_vowel and not subscript:
        independent, onset = cluster.base, ()
    elif onset[:1] and onset[0] in script.INDEPENDENT_VOWELS:
        independent, onset = onset[0], onset[1:]  # អម្ឫត: ឫ starts the second syllable
    return _SyllableBuilder(
        text=text,
        onset=onset,
        independent=independent,
        shifter=cluster.shifter,
        vowel=cluster.vowel,
        signs=_nucleus_signs(cluster.signs),
        subscript_onset=subscript,
        robat=script.ROBAT in cluster.signs and not subscript,
        silent=script.TOANDAKHIAT in cluster.signs and cluster.has_nucleus,
    )


def _close(syllable: _SyllableBuilder, letters: tuple[str, ...], text: str, signs: str):
    """Add final consonants, with the signs written on them, to an open syllable."""
    syllable.text += text
    syllable.finals += letters
    if script.BANTOC in signs:
        syllable.signs += script.BANTOC
    if script.ROBAT in signs:
        syllable.robat = True
    if script.TOANDAKHIAT in signs:
        syllable.silent_finals = True


def syllables(word: str) -> list[Syllable]:
    """Split a Khmer word into syllables. The word is normalized with pheasa first."""
    cs = clusters(normalize(word))
    if not cs:
        return []
    out: list[_SyllableBuilder] = []
    for cluster, action in zip(cs, _best_actions(cs), strict=True):
        letters = (cluster.base, *cluster.subscripts) if cluster.base else ()
        if action == _Action.FINAL:
            _close(out[-1], letters, cluster.text, cluster.signs)
        elif action == _Action.SPLIT:
            # Only robat belongs to the base; every other sign goes with the new onset.
            cut = cluster.text.index(script.COENG)
            robat = script.ROBAT if script.ROBAT in cluster.signs else ""
            _close(out[-1], (cluster.base,), cluster.text[:cut], robat)
            out.append(_start(cluster, cluster.text[cut:], cluster.subscripts, subscript=True))
        else:
            out.append(_start(cluster, cluster.text, letters, subscript=False))
    return [s.build() for s in out]
