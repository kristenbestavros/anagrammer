# Anagrammer

A command-line tool that generates name-like anagrams from words and phrases. Given any input text, it rearranges **every letter** into fictional character names that sound plausible and pronounceable.

```
$ python anagrammer.py "Software engineering"
 1. Gwenere Astion Finger
 2. Fingere Wenne Gorista
 3. Witane Ginger Fersone
 4. Fereson Genia Wingert
 5. Fria Winger Genes-Tone
 6. Grene Forise Ante-Wing
 7. Fing Trose Wina-Gerene
 8. Ster Gorine Finge-Wena
 9. Wines Tan Fer Gione-Ger
10. Son Tine Agger Wine-Fre
```

Every output is a perfect anagram of the input -- all letters used exactly once, ignoring punctuation (hyphens and apostrophes).

## How It Works

The tool uses a hybrid algorithm combining:

- **Trigram Markov chain** trained on thousands of real names from cultures worldwide to guide letter selection toward name-like sequences
- **Phonotactic rules** enforcing pronounceability constraints (valid consonant clusters, vowel requirements, syllable structure)
- **Template-based formatting** that splits letters into structured name parts (first, middle, last, initials, hyphenated surnames)
- **Hill-climbing refinement** that swaps letters between name segments to improve overall quality

For each input, the tool selects several name templates appropriate for the letter count, generates hundreds of candidates per template, scores them on a composite metric, and returns the top results.

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)

### Standard Library Modules

| Module | Purpose |
|--------|---------|
| `argparse` | CLI argument parsing |
| `collections` | `Counter` and `defaultdict` for letter/trigram frequency tracking |
| `dataclasses` | Structured template and segment definitions |
| `enum` | Segment role constants |
| `math` | Log-probability scoring |
| `pickle` | Caching trained Markov models to disk |
| `random` | Candidate generation and sampling |

### Dev Tools

| Tool | Purpose |
|------|---------|
| [Ruff](https://docs.astral.sh/ruff/) | Linting (`ruff check`) and formatting (`ruff format`) |
| [pytest](https://docs.pytest.org/) | Unit and integration tests |

## Usage

```
python anagrammer.py "phrase to anagram"
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-n`, `--count` | 15 | Number of results to show |
| `-d`, `--dataset` | `both` | Training data: `both`, `male`, or `female` |
| `--seed` | random | Random seed for reproducible output |
| `--verbose` | off | Show scores, templates, and anagram verification |
| `--no-cache` | off | Force Markov model rebuild (ignore cached model) |

### Examples

Basic usage:

```
$ python anagrammer.py "Whistleblower"
 1. Berthes Willow
 2. Bellows Wither
 3. Berthow Wellis
 4. Swillow Bether
 5. Rows Beth Wille
 6. Thows Ber Welli
 7. Lows While Bert
 8. Bell With Swore
 9. Bellow W. Hister
10. Sibert W. Howell
```

Masculine-leaning names:

```
$ python anagrammer.py "Artificial Intelligence" --dataset male
 1. Finiell Cate Rectin-Gilia
 2. Aletti Caric Ellin-Gifine
 3. Ellecti Catin Feri-Gilina
 4. Ferian Gilit Catie-Nicell
 5. Aricti Gill Elin Tane-Fice
 6. Catic Lin Ferta Gilie-Line
 7. Fine Tinie Tric Calle-Gila
 8. Ecti Lectin Gili Alian-Fer
 9. Fricate T. Gilinic-Alleine
10. Cating F. Lielieli-Terican
```

Feminine-leaning names:

```
$ python anagrammer.py "Artificial Intelligence" --dataset female
 1. Fina Crice Ellita-Gilinet
 2. Tingita Celli Frice-Elina
 3. Catlit Ellin Gericia-Fine
 4. Fing Trice Ellane-Aliciti
 5. Ficia Gent Allin Lice-Trie
 6. Ficie Tri Ling Clate-Aline
 7. Linet Catin Fra Elice-Gili
 8. Tincia Lin Fecte Ria-Gille
 9. Gillin F. Eicelina-Caritte
10. Giline I. Flettena-Caricil
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

Three datasets are available, all sourced from [Kate Monk's Onomastikon](https://tekeli.li/onomastikon/):

| Dataset | Contents | Description |
|---------|----------|-------------|
| **`both`** (default) | ~47,500 male + ~39,400 female first names + ~18,900 surnames | All names, no gender bias |
| **`male`** | ~47,500 male first names + ~18,900 surnames | Masculine-leaning patterns |
| **`female`** | ~39,400 female first names + ~18,900 surnames | Feminine-leaning patterns |

The Markov model is cached after first training for faster subsequent runs. Use `--no-cache` to force a rebuild.

## Data Sources

Name data is sourced from [Kate Monk's Onomastikon](https://tekeli.li/onomastikon/) (\u00a9 1997 Kate Monk), a comprehensive reference of names from cultures worldwide including Celtic, European, African, Asian, Middle Eastern, and Pacific traditions.

The scraping script `build_name_data.py` is included in the repo for reproducibility. It uses only the Python standard library and includes rate-limiting to be polite to the server.

## Project Structure

```
anagrammer/
    anagrammer.py         CLI entry point
    generator.py          Orchestrator: template selection, scoring, ranking
    solver.py             Core algorithm: Markov-guided construction + refinement
    markov.py             Trigram Markov chain: training, scoring, guidance
    phonotactics.py       Phonotactic constraints: onset/coda clusters, vowel rules
    templates.py          Name templates: structure definitions, formatting
    letterbag.py          Letter multiset utility
    util.py               Shared helpers
    build_name_data.py    Scraping script for name data (tekeli.li)
    data/
        male_first.txt      Male first names (~47,500)
        female_first.txt    Female first names (~39,400)
        surnames.txt        Surnames (~18,900)
        .cache/             Cached trained models (auto-generated)
```
