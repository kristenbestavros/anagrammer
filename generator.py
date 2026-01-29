"""Top-level orchestrator for anagram name generation.

Ties together the Markov model, templates, solver, and scoring into
a single interface. Handles data loading, model training, and result
ranking.
"""

import os
import sys

from letterbag import LetterBag
from markov import load_or_train
from solver import solve
from templates import (
    format_name,
    maybe_add_apostrophe,
    select_templates,
)
from util import VOWELS, normalize

# Words that should never appear as name segments
BLOCKED_WORDS = frozenset(
    {
        "ass",
        "cum",
        "die",
        "fat",
        "fag",
        "gay",
        "god",
        "hoe",
        "nig",
        "pee",
        "pig",
        "poo",
        "sex",
        "shit",
        "slut",
        "tit",
        "tits",
        "damn",
        "dick",
        "dumb",
        "fuck",
        "hell",
        "homo",
        "jerk",
        "kill",
        "piss",
        "porn",
        "rape",
        "scum",
        "thot",
        "twat",
        "wank",
        "bitch",
        "whore",
        "penis",
        "pussy",
    }
)


# Locate the data directory relative to this file
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CACHE_DIR = os.path.join(DATA_DIR, ".cache")

DATASET_FILES = {
    "real": [
        os.path.join(DATA_DIR, "real_first.txt"),
        os.path.join(DATA_DIR, "real_last.txt"),
    ],
    "fantasy": [
        os.path.join(DATA_DIR, "fantasy_names.txt"),
    ],
}

CACHE_FILES = {
    "real": os.path.join(CACHE_DIR, "real_model.pkl"),
    "fantasy": os.path.join(CACHE_DIR, "fantasy_model.pkl"),
}


def score_candidate(segments, template, model):
    """Compute a composite score for a candidate name.

    Higher is better. Combines Markov log-likelihood with several
    heuristic bonuses/penalties.
    """
    # 1. Markov log-likelihood, normalized by segment length
    markov_score = sum(model.score_segment(seg) / max(len(seg), 1) for seg in segments)

    # 2. Length balance: penalize extreme imbalance between non-initial segments
    lengths = [len(s) for s in segments if len(s) > 1]
    if len(lengths) > 1:
        mean_len = sum(lengths) / len(lengths)
        variance = sum((ln - mean_len) ** 2 for ln in lengths) / len(lengths)
        balance_bonus = -0.1 * variance
    else:
        balance_bonus = 0.0

    # 3. Vowel ratio: penalize deviation from ~40%
    full_name = "".join(segments)
    if full_name:
        vowel_ratio = sum(1 for c in full_name if c in VOWELS) / len(full_name)
        vowel_score = -10.0 * abs(vowel_ratio - 0.40)
    else:
        vowel_score = -10.0

    # 4. Starting letter diversity
    starts = set(s[0] for s in segments if s)
    diversity_bonus = 0.2 * len(starts)

    # 5. Bigram repetition penalty across segments
    bigram_sets = []
    for seg in segments:
        if len(seg) >= 2:
            bigrams = set(seg[i : i + 2] for i in range(len(seg) - 1))
            bigram_sets.append(bigrams)
    if len(bigram_sets) > 1:
        overlap = len(bigram_sets[0].intersection(*bigram_sets[1:]))
        repetition_penalty = -0.3 * overlap
    else:
        repetition_penalty = 0.0

    return (
        markov_score
        + balance_bonus
        + vowel_score
        + diversity_bonus
        + repetition_penalty
    )


SEGMENT_OVERLAP_PENALTY = 2.0


def _max_segment_overlap(candidate_segs, selected_list):
    """Max number of shared non-initial segments with any already-selected result.

    Args:
        candidate_segs: list of segment strings for the candidate
        selected_list: list of (name, score, label, segments) tuples already selected

    Returns:
        Integer count of shared segments with the most-similar selected result.
    """
    cand = {s.lower() for s in candidate_segs if len(s) > 1}
    if not cand:
        return 0
    best = 0
    for _, _, _, sel_segs in selected_list:
        sel = {s.lower() for s in sel_segs if len(s) > 1}
        shared = len(cand & sel)
        if shared > best:
            best = shared
    return best


class AnagramGenerator:
    """Main generator that produces name-like anagrams from input phrases."""

    def __init__(self, dataset="real", no_cache=False):
        """Initialize and load/train the Markov model.

        Args:
            dataset: 'real' or 'fantasy'
            no_cache: if True, force model rebuild
        """
        self.dataset = dataset

        if dataset not in DATASET_FILES:
            raise ValueError(f"Unknown dataset: {dataset}. Use 'real' or 'fantasy'.")

        data_files = DATASET_FILES[dataset]
        missing = [f for f in data_files if not os.path.exists(f)]
        if missing:
            print("Error: Training data files not found:", file=sys.stderr)
            for f in missing:
                print(f"  {f}", file=sys.stderr)
            print(
                "Ensure the data/ directory is present and populated.", file=sys.stderr
            )
            sys.exit(1)

        cache_path = CACHE_FILES.get(dataset)
        self.model = load_or_train(data_files, cache_path, force_rebuild=no_cache)

    def generate(self, phrase, n_results=15):
        """Generate name-like anagrams from a phrase.

        Args:
            phrase: input word or phrase
            n_results: number of candidates to return

        Returns:
            List of (formatted_name, score, template_label) tuples.
        """
        normalized = normalize(phrase)
        if len(normalized) < 3:
            return []

        bag = LetterBag(normalized)
        n_letters = bag.total()

        # Warn about low vowel content
        vowel_count = sum(1 for c in normalized if c in VOWELS)
        if vowel_count / n_letters < 0.15:
            print(
                "Warning: Very few vowels available. Results may be limited.",
                file=sys.stderr,
            )

        if n_letters > 30:
            print(
                "Long input detected, generation may take a moment...", file=sys.stderr
            )

        templates = select_templates(n_letters)

        # Adjust attempts based on input length
        attempts_per_template = 500
        if n_letters > 20:
            attempts_per_template = 800
        if n_letters > 30:
            attempts_per_template = 1200

        all_candidates = []

        for template in templates:
            results = solve(bag, template, self.model, n_attempts=attempts_per_template)

            for segments, _raw_score in results:
                # Skip candidates containing blocked words
                if any(seg in BLOCKED_WORDS for seg in segments):
                    continue

                # Compute composite score on clean segments (no punctuation)
                composite = score_candidate(segments, template, self.model)

                # Apply cosmetic apostrophe after scoring (rare)
                display_segments = maybe_add_apostrophe(segments, template)

                # Format the name
                name = format_name(display_segments, template)
                all_candidates.append((name, composite, template.label, segments))

        # Deduplicate by lowercased name AND by sorted segment set
        # (to avoid "Patt Silly Loy" and "Silly Patt Loy" both appearing)
        seen_names = set()
        seen_segment_sets = set()
        unique = []
        for name, score, label, segments in all_candidates:
            name_key = name.lower()
            seg_key = tuple(sorted(s.lower() for s in segments))
            if name_key not in seen_names and seg_key not in seen_segment_sets:
                seen_names.add(name_key)
                seen_segment_sets.add(seg_key)
                unique.append((name, score, label, segments))

        # Sort by composite score descending
        unique.sort(key=lambda x: x[1], reverse=True)

        # Diversity-aware selection: greedily pick results that balance
        # quality with segment-level diversity across the result set
        final = []
        label_counts = {}
        remaining = list(unique)

        while len(final) < n_results and remaining:
            best_idx = None
            best_adjusted = -float("inf")

            for i, (_name, score, label, segments) in enumerate(remaining):
                # Template diversity cap (max 40% from one template)
                count = label_counts.get(label, 0)
                max_per_label = max(2, int(n_results * 0.4))
                if count >= max_per_label:
                    continue

                # Penalize sharing segments with already-selected results
                overlap = _max_segment_overlap(segments, final)
                adjusted = score - SEGMENT_OVERLAP_PENALTY * overlap

                if adjusted > best_adjusted:
                    best_adjusted = adjusted
                    best_idx = i

            if best_idx is None:
                break

            entry = remaining.pop(best_idx)
            final.append(entry)
            label_counts[entry[2]] = label_counts.get(entry[2], 0) + 1

        # Fill remaining slots if needed (relaxed constraints)
        if len(final) < n_results:
            for entry in remaining:
                if len(final) >= n_results:
                    break
                final.append(entry)

        return final
