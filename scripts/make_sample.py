"""Cut the small sample lexicon shipped with the package out of a full build.

Keeps the most frequent words, every word that the curated chat spellings, the
evaluation set or the tests name, and the most frequent pairs among the kept words.
Run `make data` first, then `make sample`.
"""

import argparse
from collections import Counter
from pathlib import Path

from pheasa import normalize

from khmer_engine.lexicon import Lexicon, read_rows
from khmer_engine.segment import KHMER_RUN, Segmenter

PACKAGE_DATA = Path("src/khmer_engine/data")

# Files whose Khmer words must be in the sample, so tests and the evaluation run offline.
REQUIRED_FROM = [
    PACKAGE_DATA / "chat_spellings.tsv",
    Path("eval/testset.tsv"),
    Path("tests/sample_words.txt"),
]


def required_words(paths: list[Path], lexicon: Lexicon) -> set[str]:
    """Lexicon words in the Khmer text of `paths`. Phrases are segmented into words."""
    segmenter = Segmenter({w: -lexicon.logprob(w) for w in lexicon.entries}, unknown_cost=30)
    found: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                continue
            for run in KHMER_RUN.findall(line):
                found.update(w.text for w in segmenter.segment(normalize(run)) if w.known)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--build", type=Path, default=Path("data/build"))
    parser.add_argument("--out", type=Path, default=PACKAGE_DATA / "sample")
    parser.add_argument("--words", type=int, default=3000, help="most frequent words to keep")
    parser.add_argument("--pairs", type=int, default=6000, help="most frequent pairs to keep")
    args = parser.parse_args()

    rows = list(read_rows(args.build / "lexicon.tsv", 3))
    keep = {word for word, _, _ in rows[: args.words]}
    missing = required_words(REQUIRED_FROM, Lexicon.load(args.build)) - keep
    keep |= missing

    pairs: Counter[tuple[str, str]] = Counter()
    for first, second, count in read_rows(args.build / "bigrams.tsv", 3):
        if first in keep and second in keep:
            pairs[first, second] = int(count)

    args.out.mkdir(parents=True, exist_ok=True)
    header = [
        line for line in (args.build / "lexicon.tsv").read_text().splitlines() if line[:1] == "#"
    ]
    with (args.out / "lexicon.tsv").open("w", encoding="utf-8") as out:
        out.write("\n".join(header[:-1]) + "\n")
        out.write(f"# Sample: the {args.words} most frequent words plus words the tests need.\n")
        out.write(header[-1] + "\n")
        for word, count, prons in rows:
            if word in keep:
                out.write(f"{word}\t{count}\t{prons}\n")
    with (args.out / "bigrams.tsv").open("w", encoding="utf-8") as out:
        out.write(
            "# Adjacent word pairs for khmer-engine (sample), built by scripts/make_sample.py.\n"
            "# Counts: segmented khm_Khmr test split of"
            " https://huggingface.co/datasets/HuggingFaceFW/fineweb-2\n"
            "#   ODC-By 1.0, https://opendatacommons.org/licenses/by/1-0/\n"
            "# word\tnext word\tcount\n"
        )
        for (first, second), count in pairs.most_common(args.pairs):
            out.write(f"{first}\t{second}\t{count}\n")
    print(f"{len(keep)} words ({len(missing)} required beyond the top {args.words}),", end=" ")
    print(f"{min(len(pairs), args.pairs)} pairs")


if __name__ == "__main__":
    main()
