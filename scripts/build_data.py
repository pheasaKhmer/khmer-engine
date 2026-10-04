"""Build the full lexicon and word frequencies from open data.

Downloads each source once into data/raw/ (pinned to a commit and checked against its
SHA-256), then writes:

- data/build/lexicon.tsv: every Khmer word of Google's pronunciation lexicon, with its
  pronunciations and its count in the corpus
- data/build/bigrams.tsv: counts of adjacent word pairs in the corpus

Khmer does not mark word boundaries, so counting needs segmentation, and segmentation
needs counts. The script starts by preferring the fewest words, then re-segments with
costs from the previous counts.

Run it with `make data`. It needs the `data` dependency group (pyarrow).
"""

import argparse
import hashlib
import math
import re
import sys
import time
import urllib.request
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

from pheasa import normalize

from khmer_engine.segment import KHMER_RUN, Segmenter


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    page: str
    license: str
    sha256: str


GOOGLE_LEXICON = Source(
    name="google-km-lexicon.tsv",
    url="https://raw.githubusercontent.com/google/language-resources/"
    "a90601024f07ab7e96c911243324e0adeb16da96/km/data/lexicon.tsv",
    page="https://github.com/google/language-resources/tree/master/km",
    license="CC BY 4.0, https://creativecommons.org/licenses/by/4.0/",
    sha256="b3f2e700d07d6c01a4c8cac5aa2f13b9a66885668ac482cc0c513f73c56495e5",
)
FINEWEB2_KHMER = Source(
    name="fineweb2-khm-test.parquet",
    url="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/resolve/"
    "af9c13333eb981300149d5ca60a8e9d659b276b9/data/khm_Khmr/test/000_00000.parquet",
    page="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2",
    license="ODC-By 1.0, https://opendatacommons.org/licenses/by/1-0/",
    sha256="26ae4e654770b07e24a4ef6b8ef3a01c84076a920f1922ac014364ab411b84f0",
)

# A word must contain a consonant or an independent vowel; this drops entries such
# as the name of the sign ះ.
_HAS_BASE = re.compile("[\\u1780-\\u17b3]")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(source: Source, raw_dir: Path) -> Path:
    path = raw_dir / source.name
    if path.exists() and sha256(path) == source.sha256:
        return path
    raw_dir.mkdir(parents=True, exist_ok=True)
    print(f"downloading {source.url}", file=sys.stderr)
    partial = path.with_suffix(path.suffix + ".part")
    urllib.request.urlretrieve(source.url, partial)
    actual = sha256(partial)
    if actual != source.sha256:
        partial.unlink()
        raise SystemExit(f"{source.name}: expected SHA-256 {source.sha256}, got {actual}")
    partial.replace(path)
    return path


def read_pronunciations(path: Path) -> dict[str, list[str]]:
    """Khmer-script words of the Google lexicon and their transcriptions."""
    words: dict[str, list[str]] = {}
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            if line.startswith("#") or not line.strip():
                continue
            spelling, transcription = line.rstrip("\n").split("\t")[:2]
            word = normalize(spelling)
            if not KHMER_RUN.fullmatch(word) or not _HAS_BASE.search(word):
                continue
            prons = words.setdefault(word, [])
            if transcription not in prons:
                prons.append(transcription)
    return words


def read_texts(path: Path, limit: int | None) -> list[str]:
    import pyarrow.parquet as pq

    texts = pq.read_table(path, columns=["text"]).column("text").to_pylist()
    return texts[:limit] if limit else texts


# Worker state for multiprocessing: one segmenter per process.
_segmenter: Segmenter | None = None


def _init_worker(costs: dict[str, float], unknown_cost: float) -> None:
    global _segmenter
    _segmenter = Segmenter(costs, unknown_cost)


def _count(texts: list[str]) -> tuple[Counter[str], Counter[tuple[str, str]], int, int]:
    assert _segmenter is not None
    unigrams: Counter[str] = Counter()
    bigrams: Counter[tuple[str, str]] = Counter()
    known_chars = unknown_chars = 0
    for text in texts:
        for run in KHMER_RUN.findall(normalize(text)):
            previous = None
            for word in _segmenter.segment(run):
                if not word.known:
                    unknown_chars += len(word.text)
                    previous = None
                    continue
                known_chars += len(word.text)
                unigrams[word.text] += 1
                if previous is not None:
                    bigrams[previous, word.text] += 1
                previous = word.text
    return unigrams, bigrams, known_chars, unknown_chars


def _chunks(items: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def count(
    texts: list[str], costs: dict[str, float], unknown_cost: float, workers: int
) -> tuple[Counter[str], Counter[tuple[str, str]]]:
    unigrams: Counter[str] = Counter()
    bigrams: Counter[tuple[str, str]] = Counter()
    known = unknown = 0
    with Pool(workers, _init_worker, (costs, unknown_cost)) as pool:
        for u, b, k, n in pool.imap_unordered(_count, _chunks(texts, 50)):
            unigrams.update(u)
            bigrams.update(b)
            known += k
            unknown += n
    coverage = known / max(known + unknown, 1)
    words = sum(unigrams.values())
    print(f"  {words:,} words, {coverage:.1%} of characters in the lexicon", file=sys.stderr)
    return unigrams, bigrams


def costs_from(unigrams: Counter[str], words: Iterable[str]) -> tuple[dict[str, float], float]:
    """Minus log probabilities (add-one smoothing) and the cost of an unknown cluster."""
    vocabulary = list(words)
    total = sum(unigrams.values()) + len(vocabulary)
    costs = {w: -math.log((unigrams[w] + 1) / total) for w in vocabulary}
    # An unknown cluster costs more than the rarest word, so known words always win
    # where they fit.
    return costs, -math.log(1 / total) + 4.0


def write_lexicon(path: Path, prons: dict[str, list[str]], unigrams: Counter[str]) -> None:
    rows = sorted(prons, key=lambda w: (-unigrams[w], w))
    with path.open("w", encoding="utf-8") as out:
        out.write(
            "# Khmer lexicon for khmer-engine, built by scripts/build_data.py.\n"
            f"# Words and pronunciations: {GOOGLE_LEXICON.page}\n"
            f"#   Copyright 2018 Google Inc., {GOOGLE_LEXICON.license}\n"
            "#   Changed: spellings normalized with pheasa, counts added.\n"
            f"# Counts: segmented khm_Khmr test split of {FINEWEB2_KHMER.page}\n"
            f"#   {FINEWEB2_KHMER.license}\n"
            "# word\tcount\tpronunciations (separated by |)\n"
        )
        for word in rows:
            out.write(f"{word}\t{unigrams[word]}\t{'|'.join(prons[word])}\n")


def write_bigrams(path: Path, bigrams: Counter[tuple[str, str]], minimum: int) -> None:
    rows = sorted(
        ((pair, n) for pair, n in bigrams.items() if n >= minimum), key=lambda r: (-r[1], r[0])
    )
    with path.open("w", encoding="utf-8") as out:
        out.write(
            "# Adjacent word pairs for khmer-engine, built by scripts/build_data.py.\n"
            f"# Counts: segmented khm_Khmr test split of {FINEWEB2_KHMER.page}\n"
            f"#   {FINEWEB2_KHMER.license}\n"
            f"# Pairs seen fewer than {minimum} times are dropped.\n"
            "# word\tnext word\tcount\n"
        )
        for (first, second), n in rows:
            out.write(f"{first}\t{second}\t{n}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/build"))
    parser.add_argument("--limit", type=int, help="only use the first N corpus documents")
    parser.add_argument("--rounds", type=int, default=3, help="segmentation rounds")
    parser.add_argument("--min-bigram", type=int, default=3)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be at least 1")

    started = time.monotonic()
    prons = read_pronunciations(fetch(GOOGLE_LEXICON, args.raw))
    texts = read_texts(fetch(FINEWEB2_KHMER, args.raw), args.limit)
    print(f"{len(prons):,} words, {len(texts):,} documents", file=sys.stderr)

    costs: dict[str, float] = dict.fromkeys(prons, 1.0)
    unknown_cost = 2.5
    for round_number in range(1, args.rounds + 1):
        print(f"round {round_number}", file=sys.stderr)
        unigrams, bigrams = count(texts, costs, unknown_cost, args.workers)
        costs, unknown_cost = costs_from(unigrams, prons)

    args.out.mkdir(parents=True, exist_ok=True)
    write_lexicon(args.out / "lexicon.tsv", prons, unigrams)
    write_bigrams(args.out / "bigrams.tsv", bigrams, args.min_bigram)
    print(f"wrote {args.out} in {time.monotonic() - started:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
