# Data

The engine needs a Khmer word list with pronunciations, how often each word is used,
and how often words follow each other. All of it comes from openly licensed sources.

## Files

| File | Contents | License |
|---|---|---|
| `src/khmer_engine/data/sample/lexicon.tsv` | The 3,000 most frequent words, with counts and pronunciations. Shipped with the package. | Words and pronunciations: CC BY 4.0. Counts: ODC-By 1.0. |
| `src/khmer_engine/data/sample/bigrams.tsv` | The 6,000 most frequent word pairs among those words. Shipped with the package. | ODC-By 1.0 |
| `data/build/lexicon.tsv` | All 61,980 words. Built by `make data`, not committed. | Words and pronunciations: CC BY 4.0. Counts: ODC-By 1.0. |
| `data/build/bigrams.tsv` | About 209,000 word pairs seen at least 3 times. Built by `make data`, not committed. | ODC-By 1.0 |
| `data/raw/` | The downloaded sources. Not committed. | As below |

Every data file starts with comment lines that give its sources, licenses and changes,
so the attribution travels with the file. The code is MIT; the package license
expression (`MIT AND CC-BY-4.0 AND ODC-By-1.0`) covers the bundled sample.

## Sources

### Google Khmer pronunciation lexicon

- `km/data/lexicon.tsv` in
  [google/language-resources](https://github.com/google/language-resources/tree/master/km),
  pinned to commit `a906010`
- Copyright 2018 Google Inc.,
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (the repository's code is
  Apache 2.0, but this file carries its own CC BY 4.0 header)
- 62,179 Khmer-script entries, each with a phonemic transcription split into syllables
- Used for: the word list, and chat spellings derived from the pronunciations
- Changes: spellings normalized with pheasa, non-Khmer entries and entries without a
  consonant or independent vowel removed, counts added

### FineWeb-2, Khmer test split

- `data/khm_Khmr/test/000_00000.parquet` in
  [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2),
  pinned to revision `af9c133`
- [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/); the documents are web
  pages from Common Crawl, which has its own terms of use
- 16,337 documents, 34.6 million characters of Khmer web text
- Used for: word and word-pair counts only. No text from it is shipped.

## How the counts are made

Khmer does not put spaces between words, so counting words means segmenting first.
`scripts/build_data.py` normalizes each document with pheasa, splits it at spaces,
punctuation and digits, and segments each piece into lexicon words. The first round
prefers the fewest words. Each later round segments again using costs from the
previous round's counts. Three rounds give 6.5 million words, with 99.1% of Khmer
characters covered by the lexicon.

The counts come from web text, not chat, so chat-only words are rarer than they
would be in chat. Curated chat spellings make up for some of that.

## Rebuilding

```bash
make data    # downloads into data/raw/ once, writes data/build/ (about 20 s on 8 cores)
make sample  # cuts src/khmer_engine/data/sample/ out of data/build/
```

Downloads are checked against pinned SHA-256 sums. The pinned sources and checksums
are in `scripts/build_data.py`.

## Other open sources

None of these are used yet. Each could add text for counts or test data:

- [Khmer Wikipedia dumps](https://dumps.wikimedia.org/kmwiki/): CC BY-SA 4.0. Share-alike
  would apply to files derived from them.
- [NTREX-128](https://github.com/MicrosoftTranslator/NTREX) Khmer news translations:
  CC BY-SA 4.0
- The rest of FineWeb-2's Khmer data (the train split, about 2.3 GB): ODC-By 1.0
