import pytest

from khmer_engine.rules import romanize_word

# Official UNGEGN names of Cambodian provinces, written as one word. Names whose
# official form does not follow the report's own rules (Bântéay Méanchey, Preăh
# Vihéar, Rôtânôkiri, Môndól Kiri, Krŏng Preăh Sihanouk) are left out.
PROVINCES = {
    "បន្ទាយ": "bântéay",
    "បាត់ដំបង": "bătdâmbâng",
    "កំពង់ចាម": "kâmpóngcham",
    "កំពង់ឆ្នាំង": "kâmpóngchhnăng",
    "កំពង់ស្ពឺ": "kâmpóngspœ",
    "កំពង់ធំ": "kâmpóngthum",
    "កំពត": "kâmpôt",
    "កណ្ដាល": "kândal",
    "កោះកុង": "kaôhkŏng",
    "ក្រចេះ": "krâchéh",
    "ភ្នំពេញ": "phnumpénh",
    "ព្រៃវែង": "preyvêng",
    "ពោធិ៍សាត់": "poŭthĭsăt",
    "សៀមរាប": "siĕmréab",
    "ស្ទឹងត្រែង": "stœ\u0306ngtrêng",
    "ស្វាយរៀង": "svayriĕng",
    "តាកែវ": "takêv",
    "កែប": "kêb",
    "ប៉ៃលិន": "pailĭn",
    "ត្បូងឃ្មុំ": "tbongkhmŭm",
    "ឧត្តរ": "ŏtdâr",
    "ព្រះ": "preăh",
}

# Examples from the "Romanization of Khmer" article on English Wikipedia.
WIKIPEDIA = {
    "អក្សរខ្មែរ": "'âksârkhmêr",
    "កម្ពុជា": "kâmpŭchéa",
    "មណ្ឌល": "môndôl",
    "ពន្លឺ": "pônlœ",
    "សន្តិភាព": "sântĕphéap",
    "ជំនឿ": "chumnœă",
    "ទៅ": "tŏu",
}

# Worked examples from the notes of the UNGEGN report (note number in the comment).
REPORT_NOTES = {
    "កក": "kâk",  # 1
    "អង្គ": "'ângk",  # 1
    "ហ៊ាង": "héang",  # 2
    "ញ៉ង": "nhâng",  # 2
    "ខ្ពង": "khpông",  # 3
    "ល្អ": "l'â",  # 3
    "ស្វាយ": "svay",  # 3
    "ក្ដី": "kdei",  # 3
    "កន្ត្រាប់": "kântrăb",  # 3
    "ប៉ង": "pâng",  # 4
    "ប៉ាតៅ": "patau",  # 4
    "ប្លែង": "plêng",  # 4
    "ប្រាប់": "prăb",  # 4
    "ក្អែក": "k'êk",  # 5
    "ចង្អៀត": "châng'iĕt",  # 5
    "រអិល": "rô'ĕl",  # 5
    "អ្វី": "'vei",  # 5
    "អាង": "ang",  # 5
    "បត់": "bát",  # 6
    "ខ្ពស់": "khpós",  # 6
    "ចាក់": "chăk",  # 6
    "ច័ក": "chăk",  # 6
    "រពាក់": "rôpeăk",  # 6
    "មាត់": "moăt",  # 6
    "វ័ង្គ": "veăngk",  # 6
    "ភ័ព្វ": "phoăpv",  # 6
    "ធម៌": "thôrm",  # 7
    "បុណ្យ": "bŏny",  # 9
    "ពោធិ៍": "poŭthĭ",  # 9
    "ភូមិ": "phumĭ",  # 9
}


@pytest.mark.parametrize(("khmer", "expected"), PROVINCES.items())
def test_province_names(khmer, expected):
    assert romanize_word(khmer) == expected


@pytest.mark.parametrize(("khmer", "expected"), WIKIPEDIA.items())
def test_wikipedia_examples(khmer, expected):
    assert romanize_word(khmer) == expected


@pytest.mark.parametrize(("khmer", "expected"), REPORT_NOTES.items())
def test_report_examples(khmer, expected):
    assert romanize_word(khmer) == expected


def test_rules_are_applied_even_where_official_names_differ():
    # The official name is Méanchey; the rules give choăy for ជ័យ (note 6).
    assert romanize_word("មានជ័យ") == "méanchoăy"


@pytest.mark.parametrize(
    ("khmer", "expected"),
    [
        ("ឯក", "êk"),  # independent vowel with a final
        ("ឪពុក", "âupŭk"),
        ("ធ្វើ", "thveu"),
        ("ពិះ", "pĭh"),  # ិះ is not in the tables: the vowel, then h
    ],
)
def test_other_words(khmer, expected):
    assert romanize_word(khmer) == expected


def test_empty_word():
    assert romanize_word("") == ""


# Geographic Department names of Cambodian provinces (the "chat" style), as one word.
# Preăh Vihéar, Rotanak Kiri and Krong Preah Sihanouk do not follow the system's rules
# and are left out.
CHAT_PROVINCES = {
    "បន្ទាយមានជ័យ": "banteaymeanchey",
    "កំពង់ចាម": "kampongcham",
    "កំពង់ឆ្នាំង": "kampongchhnang",
    "កំពង់ស្ពឺ": "kampongspueu",
    "កំពង់ធំ": "kampongthum",
    "កំពត": "kampot",
    "កណ្ដាល": "kandal",
    "កោះកុង": "kaohkong",
    "ក្រចេះ": "kracheh",
    "មណ្ឌលគិរី": "mondolkiri",
    "ភ្នំពេញ": "phnumpenh",
    "ពោធិ៍សាត់": "pousat",
    "សៀមរាប": "siemreab",
    "ស្ទឹងត្រែង": "stuengtraeng",
    "ស្វាយរៀង": "svayrieng",
    "តាកែវ": "takaev",
    "ឧត្តរមានជ័យ": "otdarmeanchey",
    "កែប": "kaeb",
    "ប៉ៃលិន": "pailin",
    "ត្បូងឃ្មុំ": "tboungkhmum",
}

# The Geographic Department column of the Wikipedia examples.
CHAT_WIKIPEDIA = {
    "អក្សរខ្មែរ": "aksarkhmaer",
    "កម្ពុជា": "kampuchea",
    "មណ្ឌល": "mondol",
    "ពន្លឺ": "ponlueu",
    "សន្តិភាព": "santepheap",
    "ជំនឿ": "chumnoea",
    "ទៅ": "tov",
}


@pytest.mark.parametrize(("khmer", "expected"), CHAT_PROVINCES.items())
def test_chat_province_names(khmer, expected):
    assert romanize_word(khmer, "chat") == expected


@pytest.mark.parametrize(("khmer", "expected"), CHAT_WIKIPEDIA.items())
def test_chat_wikipedia_examples(khmer, expected):
    assert romanize_word(khmer, "chat") == expected


def test_chat_drops_letters_marked_silent():
    # ធិ៍ carries toandakhiat; ungegn keeps it (note 9), chat follows the pronunciation.
    assert romanize_word("ពោធិ៍", "ungegn") == "poŭthĭ"
    assert romanize_word("ពោធិ៍", "chat") == "pou"


def test_chat_has_no_apostrophes():
    assert romanize_word("ចង្អៀត", "chat") == "changiet"


def test_chat_uses_ae_for_ae_in_both_series():
    # The Geographic Department writes "Prey Veaeng"; people type "veng" or "vaeng".
    assert romanize_word("ព្រៃវែង", "chat") == "preyvaeng"


@pytest.mark.parametrize(
    ("khmer", "ungegn", "chat"),
    [
        # An independent vowel written as a subscript is the syllable's vowel.
        ("ហ្ឫទ័យ", "hrœ\u0306toăy", "hruetey"),
        ("សុហ្ឫទ", "sŏhrœ\u0306t", "sohruet"),
        ("អម្ឫត", "'âmrœ\u0306t", "amruet"),
    ],
)
def test_independent_vowel_as_subscript(khmer, ungegn, chat):
    assert romanize_word(khmer, "ungegn") == ungegn
    assert romanize_word(khmer, "chat") == chat
