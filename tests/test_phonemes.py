import pytest

from khmer_engine.phonemes import to_chat


# Transcriptions from Google's Khmer lexicon; spellings are the common chat forms,
# including every example in the project spec.
@pytest.mark.parametrize(
    ("khmer", "transcription", "expected"),
    [
        ("សុខ", "s o k", "sok"),
        ("អរគុណ", "ʔ ɑɑ . k u n", "orkun"),
        ("បង", "ɓ ɑɑ ŋ", "bong"),
        ("អូន", "ʔ oo n", "oun"),
        ("ញ៉ាំ", "ɲ a m", "nham"),
        ("បាយ", "ɓ aa j", "bay"),
        ("អត់", "ʔ ɑ t", "ot"),
        ("មាន", "m ie n", "mean"),
        ("ទេ", "t ee", "te"),
        ("ចង់", "c ɑ ŋ", "chong"),
        ("ទៅ", "t ɨ w", "tov"),
        ("ស្រី", "s r ə j", "srey"),
        ("តូច", "t oo c", "touch"),
        ("ល្អ", "l ʔ ɑɑ", "lor"),
        ("អ្នក", "n ea k", "neak"),
        ("ខ្ញុំ", "k ɲ o m", "knhom"),
        ("កម្ពុជា", "k a m . p u ʔ . c ie", "kampuchea"),
        ("ផ្ទះ", "p t ea h", "pteah"),
    ],
)
def test_chat_spellings(khmer, transcription, expected):
    assert to_chat(transcription) == expected


def test_silence_is_ignored():
    assert to_chat("sil s o k pau") == "sok"


def test_syllable_without_a_vowel():
    assert to_chat("h") == "h"


def test_unknown_phone_is_reported():
    with pytest.raises(ValueError, match="unknown phone 'x'"):
        to_chat("x a")


@pytest.mark.parametrize(
    ("transcription", "expected"),
    [
        ("s o k . s a p . ɓ aa j", "soksabay"),  # សុខសប្បាយ: ប្ប is typed once
        ("c ə t . t ɑ", "cheto"),
        ("ɓ a t . ɗ ɑ m . ɓ ɑɑ ŋ", "batdombong"),  # different letters keep both
    ],
)
def test_doubled_consonants_are_typed_once(transcription, expected):
    assert to_chat(transcription) == expected
