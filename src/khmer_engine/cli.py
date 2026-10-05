"""Command line interface.

    khmer-engine convert "sok sabay te"          # សុខសប្បាយទេ
    khmer-engine suggest "sok saba"              # ranked candidates for the last word
    khmer-engine romanize "សុខសប្បាយទេ"          # soksabay te
    khmer-engine romanize --style ungegn "..."   # sŏkhsâbbay té
    khmer-engine repl                            # try it interactively

convert and romanize read lines from standard input when no text is given.
"""

import argparse
import os
import sys
from collections.abc import Iterator
from pathlib import Path

from khmer_engine.engine import Engine
from khmer_engine.lexicon import Lexicon
from khmer_engine.user import UserDictionary

REPL_HELP = """Type romanized Khmer to see the conversion and the candidates for each word.
  :k <khmer>             romanize Khmer text
  :learn <typed> <word>  remember that <word> was picked for <typed>
  :q                     quit"""


def _engine(args: argparse.Namespace) -> Engine:
    data = args.data or os.environ.get("KHMER_ENGINE_DATA")
    user = UserDictionary(args.user) if args.user else None
    return Engine(Lexicon.load(data) if data else None, user=user)


def _texts(words: list[str]) -> Iterator[str]:
    if words:
        yield " ".join(words)
    else:
        for line in sys.stdin:
            yield line.rstrip("\n")


def _repl(engine: Engine) -> None:
    print(REPL_HELP)
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            return
        if line in (":q", ":quit"):
            return
        if line.startswith(":k "):
            khmer = line[3:]
            print(f"  chat:   {engine.romanize(khmer)}")
            print(f"  ungegn: {engine.romanize(khmer, 'ungegn')}")
        elif line.startswith(":learn "):
            parts = line.split()
            if len(parts) < 3:
                print("  usage: :learn <typed> <word>")
                continue
            engine.learn(" ".join(parts[1:-1]), parts[-1])
            print(f"  learned {parts[-1]} for {' '.join(parts[1:-1])}")
        elif line:
            result = engine.analyze(line)
            print(f"  {result.text}")
            for token in result.tokens:
                choices = "  ".join(f"{i}.{c.text}" for i, c in enumerate(token.choices, 1))
                print(f"    {token.typed}: {choices}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="khmer-engine", description="Convert between romanized Khmer and Khmer script."
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="lexicon directory, such as data/build "
        "(default: $KHMER_ENGINE_DATA, or the sample shipped with the package)",
    )
    parser.add_argument("--user", type=Path, help="JSON file to keep learned picks in")
    commands = parser.add_subparsers(dest="command", required=True)
    convert = commands.add_parser("convert", help="romanized Khmer to Khmer script")
    convert.add_argument("text", nargs="*", help="text to convert (default: standard input)")
    suggest = commands.add_parser("suggest", help="ranked Khmer candidates for the last word")
    suggest.add_argument("text", nargs="+")
    suggest.add_argument("-n", type=int, default=5, help="how many (default 5)")
    romanize = commands.add_parser("romanize", help="Khmer script to romanized text")
    romanize.add_argument("text", nargs="*", help="text to romanize (default: standard input)")
    romanize.add_argument("--style", choices=["chat", "ungegn"], default="chat")
    commands.add_parser("repl", help="type romanized Khmer and see candidates as you go")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    engine = _engine(args)
    if args.command == "convert":
        for text in _texts(args.text):
            print(engine.convert(text))
    elif args.command == "romanize":
        for text in _texts(args.text):
            print(engine.romanize(text, args.style))
    elif args.command == "suggest":
        for i, s in enumerate(engine.suggest(" ".join(args.text), args.n), 1):
            print(f"{i}. {s.text}\t{s.score:.1f}\t{s.source}")
    else:
        _repl(engine)
    return 0
