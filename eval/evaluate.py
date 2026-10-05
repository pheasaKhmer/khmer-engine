"""Measure how well the engine converts chat romanization, and how fast.

    uv run python eval/evaluate.py                     # bundled sample lexicon
    uv run python eval/evaluate.py --data data/build   # full lexicon
    uv run python eval/evaluate.py --failures          # list the phrases it gets wrong
    uv run python eval/evaluate.py --testset eval/native.tsv  # typed by a native speaker

Accuracy: for each (romanized, Khmer) pair in the test set, whether the best conversion
is right (top 1) and whether the right one is among the five best (top 5). Phrases of
several words are also tried with their spaces removed, as people often type them.

Latency: `suggest` is called on every prefix of 5-word inputs, as a keyboard calls it
on every keystroke. The spec's target is under 10 ms.
"""

import argparse
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from pheasa import normalize

from khmer_engine.engine import Engine
from khmer_engine.lexicon import Lexicon, read_rows

TESTSET = Path(__file__).with_name("testset.tsv")
LATENCY_TARGET_MS = 10.0


@dataclass
class Row:
    romanized: str
    khmer: str
    reviewed: bool


@dataclass
class Score:
    total: int = 0
    top1: int = 0
    top5: int = 0

    def add(self, top1: bool, top5: bool) -> None:
        self.total += 1
        self.top1 += top1
        self.top5 += top5

    def line(self, name: str) -> str:
        if not self.total:
            return f"  {name:24} {0:>5}      -      -"
        return (
            f"  {name:24} {self.total:>5} {self.top1 / self.total:>6.1%} "
            f"{self.top5 / self.total:>6.1%}"
        )


def read_testset(path: Path) -> list[Row]:
    return [Row(r, normalize(k), v.strip() == "yes") for r, k, v in read_rows(path, 3)]


def check(engine: Engine, typed: str, expected: str) -> tuple[bool, bool, str]:
    readings = [normalize(a) for a in engine.analyze(typed, 5).alternatives]
    return readings[0] == expected, expected in readings, readings[0]


def five_word_inputs(rows: list[Row], count: int = 20) -> list[str]:
    """Inputs of exactly five typed words, made by joining test phrases."""
    words = [w for row in rows for w in row.romanized.split()]
    return [" ".join(words[i : i + 5]) for i in range(0, min(len(words) - 4, count * 5), 5)]


def latency(engine: Engine, inputs: list[str]) -> list[float]:
    times = []
    for text in inputs:
        for end in range(1, len(text) + 1):
            started = time.perf_counter()
            engine.suggest(text[:end])
            times.append((time.perf_counter() - started) * 1000)
    return sorted(times)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data", type=Path, help="lexicon directory (default: the sample)")
    parser.add_argument("--testset", type=Path, default=TESTSET)
    parser.add_argument("--failures", action="store_true", help="list wrong conversions")
    parser.add_argument("--min-top1", type=float, help="fail if top-1 accuracy is lower")
    args = parser.parse_args()

    started = time.perf_counter()
    lexicon = Lexicon.load(args.data) if args.data else Lexicon.sample()
    engine = Engine(lexicon)
    startup = time.perf_counter() - started
    rows = read_testset(args.testset)

    scores = {
        name: Score()
        for name in ("all", "reviewed", "one word", "several words", "  without spaces")
    }
    failures = []
    for row in rows:
        top1, top5, got = check(engine, row.romanized, row.khmer)
        scores["all"].add(top1, top5)
        if row.reviewed:
            scores["reviewed"].add(top1, top5)
        several = " " in row.romanized
        scores["several words" if several else "one word"].add(top1, top5)
        if not top1:
            failures.append((row.romanized, row.khmer, got))
        if several:
            joined_top1, joined_top5, _ = check(engine, row.romanized.replace(" ", ""), row.khmer)
            scores["  without spaces"].add(joined_top1, joined_top5)

    times = latency(engine, five_word_inputs(rows))
    p95 = times[int(len(times) * 0.95)]

    print(f"lexicon:  {args.data or 'sample'} ({len(lexicon):,} words)")
    shown = os.path.relpath(args.testset)
    print(f"test set: {shown} ({len(rows)} phrases, {scores['reviewed'].total} reviewed)")
    print()
    print(f"  {'':24} {'count':>5} {'top 1':>6} {'top 5':>6}")
    for name, score in scores.items():
        print(score.line(name))
    print()
    print(f"suggest per keystroke, 5-word inputs ({len(times)} calls):")
    print(
        f"  median {statistics.median(times):.1f} ms, p95 {p95:.1f} ms, max {times[-1]:.1f} ms"
        f" (target under {LATENCY_TARGET_MS:.0f} ms)"
    )
    print(f"engine start: {startup:.1f} s")
    if args.failures and failures:
        print("\nwrong top 1 (typed, expected, got):")
        for typed, expected, got in failures:
            print(f"  {typed:28} {expected}  {got}")

    accuracy = scores["all"].top1 / scores["all"].total
    if args.min_top1 is not None and accuracy < args.min_top1:
        print(f"\ntop-1 accuracy {accuracy:.1%} is below {args.min_top1:.1%}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
