# Anagrammer

A command-line tool that generates name-like anagrams from words and phrases. Given any input text, it rearranges **every letter** into fictional character names that sound plausible and pronounceable.

```
$ python anagrammer.py "William Shakespeare"
 1. Maiker Wille Pashaes
 2. Piasham Welle Karise
 3. Hamaki Wille Paseres
 4. Kespale Hamira Wiles
 5. Pleshes Marie Kawlia
 6. Amikas Welle Pearish
 7. Piela Wales Maki-Sher
 8. Pass Welle Marie-Haki
 9. Wiell Mashie Per-Saka
10. Kesse Hamara Will-Pie
```

Every output is a **perfect anagram** of the input -- all letters used exactly once, none added.

## How It Works

The tool uses a hybrid algorithm combining:

- **Trigram Markov chain** trained on thousands of real or fantasy names to guide letter selection toward name-like sequences
- **Phonotactic rules** enforcing pronounceability constraints (valid consonant clusters, vowel requirements, syllable structure)
- **Template-based formatting** that splits letters into structured name parts (first, middle, last, initials, hyphenated surnames)
- **Hill-climbing refinement** that swaps letters between name segments to improve overall quality

For each input, the tool selects several name templates appropriate for the letter count, generates hundreds of candidates per template, scores them on a composite metric, and returns the top results.

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)

## Usage

```
python anagrammer.py "phrase to anagram"
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-n`, `--count` | 15 | Number of results to show |
| `-d`, `--dataset` | `real` | Training data: `real` or `fantasy` |
| `--seed` | random | Random seed for reproducible output |
| `--verbose` | off | Show scores, templates, and anagram verification |
| `--no-cache` | off | Force Markov model rebuild (ignore cached model) |

### Examples

Basic usage:

```
$ python anagrammer.py "Whistleblower"
 1. Thowes Ber Will
 2. Will Bowes Ther
 3. Ber Towes Whill
 4. Ber Will Hestow
 5. Boweh Ster Will
 6. Herbow Will Ste
 7. Browest H. Wille
 8. Berist W. Howell
 9. Willert H. Bowes
10. Howes B. Willert
```

Fantasy-style names:

```
$ python anagrammer.py "Artificial Intelligence" --dataset fantasy
 1. Ariele Lintic Gale-Fintic
 2. Fale Tilint Grien-Eliacic
 3. Ale Tiline Firenic-Galtic
 4. Glara Inten Fiel-Eilitcic
 5. Elintic Gricel Falia-Tine
 6. Aringil Cael Icite-Fintel
 7. Falinte C. Ariele Gilintic
 8. Calenci G. Tiftiel-Arineil
 9. Aleric T. Ilinefic-Galinte
10. Caelin E. Feltilia-Grintic
```

Fewer results with verbose scoring:

```
$ python anagrammer.py "Split Loyalty" -n 5 --verbose
Input: "Split Loyalty" (12 letters: ailllopsttyy)

  1. Patt Silly Loy                 [score:    -7.7] [First Middle Last] [OK]
  2. Silly Pott Lay                 [score:    -7.7] [First Middle Last] [OK]
  3. Patty Loy Sill                 [score:    -7.8] [First Middle Last] [OK]
  4. Yott Silly Pal                 [score:    -7.8] [First Middle Last] [OK]
  5. Aly Pott Silly                 [score:    -7.9] [First Middle Last] [OK]
```

Reproducible output:

```
$ python anagrammer.py "Hello World" --seed 42
$ python anagrammer.py "Hello World" --seed 42   # identical output
```

## Name Formats

The tool automatically selects name structures based on input length:

| Input Length | Formats Generated |
|---|---|
| 3-5 letters | Mononym, I. Last |
| 6 letters | Mononym, I. Last, First Last |
| 7-10 letters | Mononym, First Last, First M. Last, and others as length allows |
| 11-15 letters | First Last, First M. Last, First Middle Last, First M. M. Last |
| 16+ letters | All above plus hyphenated variants (e.g. First M. Last-Last) |

Multiple formats appear in each run for variety. Cosmetic punctuation (initials with `.`, hyphenated surnames, rare apostrophes like O'Brien) is applied for stylistic diversity.

## Training Data

Two datasets are included:

- **`real`** (default) -- ~13,000 real-world first names and surnames from diverse cultural origins, producing grounded-sounding results
- **`fantasy`** -- ~2,500 fantasy and fictional names (elvish, dwarven, mystical styles), producing results suited for fantasy settings

The Markov model is cached after first training for faster subsequent runs. Use `--no-cache` to force a rebuild.

## Project Structure

```
anagrammer/
    anagrammer.py       CLI entry point
    generator.py        Orchestrator: template selection, scoring, ranking
    solver.py           Core algorithm: Markov-guided construction + refinement
    markov.py           Trigram Markov chain: training, scoring, guidance
    phonotactics.py     Phonotactic constraints: onset/coda clusters, vowel rules
    templates.py        Name templates: structure definitions, formatting
    letterbag.py        Letter multiset utility
    util.py             Shared helpers
    data/
        real_first.txt      Real first names
        real_last.txt       Real surnames
        fantasy_names.txt   Fantasy/fictional names
        .cache/             Cached trained models (auto-generated)
```
