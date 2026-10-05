"""Convert chat-style romanized Khmer to Khmer script and back."""

import os
from functools import cache

from khmer_engine.engine import Engine, Suggestion
from khmer_engine.lexicon import Lexicon
from khmer_engine.romanize import Style

__version__ = "0.1.0.dev0"

__all__ = [
    "Engine",
    "Lexicon",
    "Style",
    "Suggestion",
    "__version__",
    "convert",
    "default_engine",
    "romanize",
    "suggest",
]


@cache
def default_engine() -> Engine:
    """The engine behind the module-level functions. It loads the lexicon directory named
    by the KHMER_ENGINE_DATA environment variable, or the sample shipped with the package."""
    data = os.environ.get("KHMER_ENGINE_DATA")
    return Engine(Lexicon.load(data) if data else None)


def suggest(text: str, n: int = 5) -> list[Suggestion]:
    """The n most likely Khmer readings of the last word of romanized `text`."""
    return default_engine().suggest(text, n)


def convert(text: str) -> str:
    """The most likely Khmer for romanized `text`."""
    return default_engine().convert(text)


def romanize(khmer: str, style: Style = "chat") -> str:
    """Romanize Khmer text, in the "chat" style people type or the "ungegn" standard."""
    return default_engine().romanize(khmer, style)
