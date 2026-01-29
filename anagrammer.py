#!/usr/bin/env python3
"""Anagrammer: Generate name-like anagrams from words and phrases.

Usage:
    python anagrammer.py "Whistleblower"
    python anagrammer.py "Pride goes before the fall" --dataset fantasy -n 8
    python anagrammer.py "Split Loyalty" --seed 42 --verbose
"""

import argparse
import random
import sys

from generator import AnagramGenerator
from letterbag import LetterBag
from util import normalize


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate name-like anagrams from a word or phrase.",
    )
    parser.add_argument(
        "phrase",
        help="Word or phrase to anagram",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=15,
        help="Number of name candidates to generate (default: 15)",
    )
    parser.add_argument(
        "-d",
        "--dataset",
        choices=["real", "fantasy"],
        default="real",
        help="Training dataset: 'real' for census names, 'fantasy' for fictional names",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible output",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show scores and template details",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force Markov model rebuild, ignoring cached model",
    )
    return parser.parse_args()


def validate_input(phrase):
    """Validate the input phrase and return normalized letters."""
    # Check for non-ASCII
    non_ascii = [c for c in phrase if ord(c) > 127]
    if non_ascii:
        chars = "".join(set(non_ascii))
        print(f"Warning: Non-ASCII characters ignored: {chars}", file=sys.stderr)

    normalized = normalize(phrase)

    if not normalized:
        print("Error: Input must contain at least one letter.", file=sys.stderr)
        sys.exit(1)

    if len(normalized) < 3:
        print(
            "Error: Input must contain at least 3 letters to generate a name.",
            file=sys.stderr,
        )
        sys.exit(1)

    return normalized


def verify_anagram(original_phrase, generated_name):
    """Verify that a generated name is a perfect anagram of the input."""
    original = LetterBag(original_phrase)
    result = LetterBag(generated_name)
    return original == result


def main():
    args = parse_args()

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)

    # Validate input
    normalized = validate_input(args.phrase)
    bag = LetterBag(normalized)

    # Show input info in verbose mode
    if args.verbose:
        print(
            f'Input: "{args.phrase}" ({bag.total()} letters: {bag.as_sorted_string()})'
        )
        print()

    # Generate
    gen = AnagramGenerator(dataset=args.dataset, no_cache=args.no_cache)
    results = gen.generate(args.phrase, n_results=args.count)

    if not results:
        print(
            "Could not generate any valid names from this input."
            " Try a different phrase.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Display results
    for i, (name, score, label, _segments) in enumerate(results, 1):
        if args.verbose:
            # Verify anagram property
            is_valid = verify_anagram(args.phrase, name)
            status = "OK" if is_valid else "MISMATCH"
            print(f"{i:>3}. {name:<30} [score: {score:>7.1f}] [{label}] [{status}]")
        else:
            print(f"{i:>3}. {name}")


if __name__ == "__main__":
    main()
