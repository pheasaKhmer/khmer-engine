# khmer-engine

Convert chat-style romanized Khmer to Khmer script, and Khmer script back to romanized text.

Many people type Khmer with Latin letters in chats because the Khmer keyboard is slow. Given
`sok sabay te`, the engine gives សុខសប្បាយទេ, with ranked alternatives for each word. Given Khmer
script, it gives readable romanized text in the way people type it (`soksabay te`) or in the
UNGEGN standard (`sŏkhsâbbay té`). Chat romanization has no standard, so the engine is built to
accept the many spellings one word gets: "sous dey", "suosdey" and "sursdey" all give សួស្តី.

Examples marked † are ones a native speaker should double-check (see
[Checking the Khmer](#checking-the-khmer)).

## Try it

```bash
uv sync
uv run khmer-engine convert "nham bai hoy nov"    # ញ៉ាំបាយហើយនៅ †
uv run khmer-engine suggest "orku"                # 1. អរគុណ ... (completes the word being typed)
uv run khmer-engine romanize "ខ្ញុំស្រឡាញ់អូន។"       # khnhom srolanh oun. †
uv run khmer-engine romanize --style ungegn "ភ្នំពេញ" # phnumpénh
uv run khmer-engine repl                          # type and see candidates for each word
```

`convert` and `romanize` read lines from standard input when no text is given. `--data
data/build` uses the full lexicon (see [Data](#data)) instead of the sample shipped with the
package, and `--user picks.json` keeps learned picks between runs.

From Python:

```python
import khmer_engine

khmer_engine.convert("sok sabay te")  # 'សុខសប្បាយទេ'
[s.text for s in khmer_engine.suggest("orku", 3)]  # ['អរគុណ', 'ក៏', 'គូ']
khmer_engine.romanize("សុខសប្បាយទេ")  # 'soksabay te'
khmer_engine.romanize("សុខសប្បាយទេ", "ungegn")  # 'sŏkhsâbbay té'
```

The module functions share one engine, which loads the directory named by
`KHMER_ENGINE_DATA` or the bundled sample. For more control, make your own:

```python
from khmer_engine import Engine, Lexicon
from khmer_engine.user import UserDictionary

engine = Engine(Lexicon.load("data/build"), user=UserDictionary("picks.json"))
result = engine.analyze("bong srolanh oun")  # best text, n-best alternatives, choices per word
engine.learn("bong", "បង់")  # picked candidates rank higher next time
```

Each suggestion has `text`, `score`, `source` and the `start`/`end` of the input it
replaces, so a keyboard knows what to swap out.

## How it works

### Romanized → Khmer

**1. A lexicon with pronunciations.** 61,980 Khmer words from Google's pronunciation
lexicon, each with a phonemic transcription, and how often each word and each pair of
words appears in 6.5 million words of Khmer web text.

**2. Several romanizations per word.** Each word is indexed under:

| Source | From | អរគុណ | ភ្នំពេញ |
|---|---|---|---|
| pronunciation | the transcription, as people type by sound | `orkun` | `pnumpenh` |
| spelling | rule-based chat style (the Geographic Department system) | `arkun` | `phnumpenh` |
| ungegn | the UNGEGN standard, diacritics removed | `arkun` | `phnumpenh` |
| curated | a short hand-written list (`data/chat_spellings.tsv`) | `orkun` | |

The curated list is for spellings nothing predicts, such as abbreviations: `jg` for ចង់.

**3. Matching keys.** A key folds the spelling variants of chat romanization so they
coincide:

| Folded | Example |
|---|---|
| o/ou/u/ao, e/ae/eu/i, ea/ia/ie | `touch`, `toch`, `tuch` → `tOc` |
| c/ch/j, k/kh/g, p/ph, t/th, w/v, nh/ny | `chong`, `jong` → `cON` |
| r after a vowel; h or s at the end | `orkun`, `okun` → `OkOn`; `preah`, `prea` → `prJ` |
| doubled letters; a final i as y | `sabbay`, `sabay`, `sabai` → `sAbAy` |
| diacritics and apostrophes | `Kâmpŭchéa`, `kampuchea` → `kAmpOcJ` |

**4. Candidates for a word.** Every word whose key matches the typed key, or is one edit
away from it, is a candidate. Candidates are scored by whether the key needed an edit, by
the letter distance between what was typed and the closest romanization of the word, and by
how common the word is.

**5. Sentences.** A Viterbi search picks the sequence of words with the best total of
candidate scores and bigram probabilities, so context decides between words that sound
alike:

```
bong srolanh oun  →  បងស្រលាញ់អូន  (បង, "older sibling")  †
bong luy          →  បង់លុយ        (បង់, "to pay")       †
```

A word may be typed across spaces (`or kun` → អរគុណ), several words without spaces
(`soksabayte` → សុខសប្បាយទេ), and English mixed in (`ot mean wifi te` → អត់មាន wifi ទេ).
English words on a list stay as typed, at a cost, so a good Khmer reading still wins.
A word nothing reads is spelled syllable by syllable from a table learned from the lexicon
(`knhom chmous sreymom` → ខ្ញុំឈ្មោះស្រីមុំ †), or kept as typed.

**6. Learning.** A picked candidate is counted under the key of what was typed and ranks
higher next time, for that spelling and its variants. Picks stay on the device, in memory
or in a JSON file.

### Khmer → romanized

1. Normalize with [pheasa](https://github.com/pheasaKhmer/pheasa), so text that looks the same
   gives the same result (coeng da and coeng ta, the order of marks, Khmer digits).
2. Split each run of Khmer into words with the lexicon (dynamic programming over word
   frequencies, never inside a written cluster).
3. Romanize each word:
   - **chat**: from its pronunciation, the way people type it, with the aspiration of a
     first consonant taken from the spelling (ភ្នំ is /pnum/, but people type "phnum"). Words
     the lexicon lacks follow the chat spelling rules.
   - **ungegn**: from its spelling, following the 2013 UNGEGN report.

```
សុខសប្បាយទេ       →  soksabay te        | sŏkhsâbbay té
ខ្ញុំស្រឡាញ់អូន។  →  khnhom srolanh oun. | khnhom srâlănh on.  †
```

### The spelling rules

Romanizing from the spelling means finding syllables first. Khmer writes the final
consonant of one syllable as the base of the next written cluster: in កម្ពុជា the ម closes
"kam" and the ព under it starts "pu". `syllables.py` scores the possible readings and
keeps the cheapest. `rules.py` then applies the tables and all 11 notes of the
[UNGEGN report](https://www.eki.ee/wgrs/rom1_km.pdf) (series of subscripts and shifters,
bantoc, samyok sannya, robat, apostrophes), or the Geographic Department system for the
chat style. Tests check the official province names in both systems and the worked
example in the report.

## Data

All data comes from openly licensed sources, pinned and checksummed:

- **Words and pronunciations**: Google's Khmer lexicon, CC BY 4.0
- **Word and pair counts**: the Khmer test split of FineWeb-2, ODC-By 1.0

The package ships a sample with the 3,000 most frequent words plus the words the tests
need, so everything works offline. Build the full lexicon (about 20 seconds) with:

```bash
make data       # downloads into data/raw/ once, writes data/build/
uv run khmer-engine --data data/build convert "sous dey bong"
```

[data/README.md](data/README.md) lists every file with its source, license and changes.

## Evaluation

```bash
make eval                                            # bundled sample
uv run python eval/evaluate.py --data data/build --failures
```

On the 126 phrases of `eval/testset.tsv`:

| | Sample (3,008 words) | Full (61,980 words) |
|---|---|---|
| Top 1, all phrases | 86.5% | 92.1% |
| Top 5, all phrases | 96.0% | 96.8% |
| Top 1, phrases of several words | 88.3% | 95.7% |
| Top 1, the same typed without spaces | 80.9% | 88.3% |
| `suggest` per keystroke, 5-word input | median 0.2 ms, max 1.1 ms | median 0.6 ms, max 3.5 ms |
| Engine start | 0.1 s | 4.1 s |

The spec's target is under 10 ms per keystroke for a 5-word input. Most remaining errors
need more context than one phrase gives (`lok` is លក់ "sell" or លោក "sir"), or are a choice
between two spellings in common use (ស្រឡាញ់ and ស្រលាញ់). The test set has not been reviewed
by a native speaker yet, so treat these numbers as provisional.

## Checking the Khmer

These need a native speaker. Each data file has a `reviewed` column to fill in.

- `eval/testset.tsv`: all 126 phrases and their Khmer
- `src/khmer_engine/data/chat_spellings.tsv`: the 25 curated chat spellings
- Choices in `phonemes.py` about how sounds are typed: short ɨ as `e` (`penh`, `nek`),
  long ɑ without a final as `or` (`orkun`, `lor`), ទៅ as `tov`
- Which spelling to prefer when two are common: ស្រឡាញ់ (dictionary) or ស្រលាញ់ (output now)
- The examples marked † in this README

## Porting to C++ or Rust

The design keeps a port small. Data files are tab-separated text. Matching keys are a
lookup table. The fuzzy step generates the keys one edit away instead of using an index of
deletions. The decoder is a beam Viterbi over letter positions, and segmentation is a
one-pass dynamic program. The only outside dependency is Khmer normalization (pheasa),
which a port has to reimplement or call. For a keyboard, the index of romanization keys
should be built once when the data is built and stored in a compact read-only file (a
trie or FST), instead of computed at start-up as the Python version does.

## Development

```bash
make check    # ruff, pytest, and the evaluation on the sample (fails below 85% top 1)
make format
make data     # full lexicon into data/build/
make sample   # regenerate the bundled sample from data/build/
```

## Related

- [khmer-keyboard](https://github.com/pheasaKhmer/khmer-keyboard): iOS and Android keyboard built on this engine
- [khmer-converter](https://github.com/pheasaKhmer/khmer-converter): web page and Telegram bot built on this engine

## License

The code is [MIT](LICENSE). The bundled sample data keeps the licenses of its sources: CC BY
4.0 for the words and pronunciations, ODC-By 1.0 for the counts (see
[data/README.md](data/README.md)).
