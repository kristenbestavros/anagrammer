# Project Overview

A command-line tool that generates name-like anagrams from words and phrases. Given any input text, it rearranges **every letter** into fictional character names that sound plausible and pronounceable.

## Commands

- Lint: `ruff check . --fix`
- Format: `ruff format .`
- Test: `pytest`
- Run: python anagrammer.py "phrase here"

## Workflow

1. Always read README.md before starting; if no README.md exists, create one when finished.
2. Run `ruff check . --fix && ruff format .` after changes
3. Run `pytest` before finishing if tests exist
4. Always update README.md when adding features or changing setup
5. Ask before adding complexity — favor simplicity when possible
6. When modifying scoring or generation, run a quick manual test: python anagrammer.py "Split Loyalties" --seed 42 --verbose and verify outputs are valid anagrams

## Architecture

The pipeline flows: anagrammer.py (CLI) → src/generator.py (orchestrator) → src/solver.py (generation + refinement) → src/markov.py (trigram model)

Key design points:

- src/solver.py: Builds segments char-by-char with Markov guidance, then refines via hill-climbing letter swaps. Temperature escalates from TEMP_MIN to TEMP_MAX across attempts.
- src/generator.py: score_candidate() computes composite score from per-segment Markov scores, length balance, vowel ratio, and other heuristics. BLOCKED_WORDS filters offensive segments.
- src/phonotactics.py: Rule-based constraints on consonant clusters, vowel placement, syllable structure.
- src/templates.py: Defines name structures (First Last, First M. Last, etc.) with segment specs.
- Source modules live in src/ (as a Python package with relative imports). CLI entry points (anagrammer.py, main.py) and build_name_data.py stay in the project root. Data files are in data/.

## Documentation

All docs go in README.md unless told otherwise. Do not create extra markdown files.
