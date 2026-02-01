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
    SegmentRole,
    format_name,
    get_template_by_label,
    list_templates,
    maybe_add_apostrophe,
    relax_template,
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

_MALE_FIRST = os.path.join(DATA_DIR, "male_first.txt")
_FEMALE_FIRST = os.path.join(DATA_DIR, "female_first.txt")
_SURNAMES = os.path.join(DATA_DIR, "surnames.txt")

DATASET_FILES = {
    "both": [_MALE_FIRST, _FEMALE_FIRST, _SURNAMES],
    "male": [_MALE_FIRST, _SURNAMES],
    "female": [_FEMALE_FIRST, _SURNAMES],
}

CACHE_FILES = {
    "both": os.path.join(CACHE_DIR, "both_model.pkl"),
    "male": os.path.join(CACHE_DIR, "male_model.pkl"),
    "female": os.path.join(CACHE_DIR, "female_model.pkl"),
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


def _max_segment_overlap(candidate_segs, selected_list, ignore_indices=None):
    """Max number of shared non-initial segments with any already-selected result.

    Args:
        candidate_segs: list of segment strings for the candidate
        selected_list: list of (name, score, label, segments) tuples already selected
        ignore_indices: optional set of segment indices to exclude from comparison
            (e.g., fixed segments that will always overlap)

    Returns:
        Integer count of shared segments with the most-similar selected result.
    """
    ignore = ignore_indices or set()
    cand = {
        s.lower()
        for i, s in enumerate(candidate_segs)
        if len(s) > 1 and i not in ignore
    }
    if not cand:
        return 0
    best = 0
    for _, _, _, sel_segs in selected_list:
        sel = {
            s.lower() for i, s in enumerate(sel_segs) if len(s) > 1 and i not in ignore
        }
        shared = len(cand & sel)
        if shared > best:
            best = shared
    return best


def _parse_fixed_last(fixed_last):
    """Parse a --last value into (last_text, hyph_last_text).

    Supports three forms:
        "Jones"       → ("jones", None)        primary LAST slot
        "-Jones"      → (None, "jones")         HYPHENATED_LAST slot
        "Smith-Jones" → ("smith", "jones")      both slots
        "Jones-"      → ("jones", None)         trailing hyphen stripped

    Returns (str_or_None, str_or_None).
    """
    if not fixed_last:
        return None, None

    raw = fixed_last.strip()
    if raw.startswith("-") and len(raw) > 1:
        # "-Jones" → second position only
        text = normalize(raw[1:])
        return None, text if text else None
    elif "-" in raw:
        # "Smith-Jones" or "Jones-"
        parts = raw.split("-", 1)
        left = normalize(parts[0])
        right = normalize(parts[1]) if parts[1] else None
        return left or None, right
    else:
        # "Jones" → primary position
        text = normalize(raw)
        return text if text else None, None


def _build_fixed_segments(template, fixed_first=None, fixed_last=None):
    """Map fixed names to their segment indices in a template.

    Returns a dict of {segment_index: lowercase_string}.
    Only maps the first matching segment for each role.
    Handles hyphenated --last values via _parse_fixed_last().
    """
    last_text, hyph_last_text = _parse_fixed_last(fixed_last)

    fixed = {}
    first_found = False
    last_found = False
    hyph_found = False
    for i, spec in enumerate(template.segments):
        if fixed_first and spec.role == SegmentRole.FIRST and not first_found:
            fixed[i] = normalize(fixed_first)
            first_found = True
        if last_text and spec.role == SegmentRole.LAST and not last_found:
            fixed[i] = last_text
            last_found = True
        if (
            hyph_last_text
            and spec.role == SegmentRole.HYPHENATED_LAST
            and not hyph_found
        ):
            fixed[i] = hyph_last_text
            hyph_found = True
    return fixed


class AnagramGenerator:
    """Main generator that produces name-like anagrams from input phrases."""

    def __init__(self, dataset="both", no_cache=False):
        """Initialize and load/train the Markov model.

        Args:
            dataset: 'both', 'male', or 'female'
            no_cache: if True, force model rebuild
        """
        self.dataset = dataset

        if dataset not in DATASET_FILES:
            raise ValueError(
                f"Unknown dataset: {dataset}. Use 'both', 'male', or 'female'."
            )

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

    def generate(
        self,
        phrase,
        n_results=15,
        template_label=None,
        fixed_first=None,
        fixed_last=None,
    ):
        """Generate name-like anagrams from a phrase.

        Args:
            phrase: input word or phrase
            n_results: number of candidates to return
            template_label: optional template label to use exclusively
            fixed_first: optional fixed first name string
            fixed_last: optional fixed last name string

        Returns:
            List of (formatted_name, score, template_label, segments) tuples.
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

        # Determine required roles from fixed segments
        required_roles = set()
        if fixed_first:
            required_roles.add(SegmentRole.FIRST)
        if fixed_last:
            last_text, hyph_last_text = _parse_fixed_last(fixed_last)
            if last_text:
                required_roles.add(SegmentRole.LAST)
            if hyph_last_text:
                required_roles.add(SegmentRole.HYPHENATED_LAST)

        # Template selection
        if template_label:
            template_obj = get_template_by_label(template_label)
            if template_obj is None:
                available = ", ".join(f"'{label}'" for label, _, _ in list_templates())
                print(
                    f"Error: Unknown template '{template_label}'."
                    f" Available: {available}",
                    file=sys.stderr,
                )
                return []
            # Validate it has required roles
            template_roles = {s.role for s in template_obj.segments}
            for role in required_roles:
                if role not in template_roles:
                    print(
                        f"Error: Template '{template_label}' does not have"
                        f" a {role.value} segment.",
                        file=sys.stderr,
                    )
                    return []
            templates = [template_obj]
        else:
            templates = select_templates(
                n_letters, required_roles=required_roles or None
            )

        # Calculate remaining letters after fixed segments
        remaining_bag = bag.copy()
        if fixed_first:
            remaining_bag.subtract(normalize(fixed_first))
        if fixed_last:
            remaining_bag.subtract(normalize(fixed_last))
        remaining_count = remaining_bag.total()

        # Filter templates for viability with fixed segments
        if fixed_first or fixed_last:
            viable = []
            for t in templates:
                fixed_map = _build_fixed_segments(t, fixed_first, fixed_last)
                # Check that fixed name lengths are compatible with specs
                ok = True
                for idx, text in fixed_map.items():
                    spec = t.segments[idx]
                    if len(text) < spec.min_len or len(text) > spec.max_len:
                        ok = False
                        break
                if not ok:
                    # If user explicitly chose this template, try relaxing it
                    if template_label:
                        relaxed = relax_template(t, n_letters)
                        if relaxed is not None:
                            t = relaxed
                            # Re-check with relaxed bounds
                            fixed_map = _build_fixed_segments(
                                t, fixed_first, fixed_last
                            )
                            ok = True
                            for idx, text in fixed_map.items():
                                spec = t.segments[idx]
                                if len(text) < spec.min_len or len(text) > spec.max_len:
                                    ok = False
                                    break
                    if not ok:
                        continue
                # Check that remaining letters fit the non-fixed segments
                non_fixed_min = sum(
                    s.min_len for i, s in enumerate(t.segments) if i not in fixed_map
                )
                non_fixed_max = sum(
                    s.max_len for i, s in enumerate(t.segments) if i not in fixed_map
                )
                if non_fixed_min <= remaining_count <= non_fixed_max:
                    viable.append(t)
                elif template_label:
                    # User explicitly chose this template, try relaxing
                    relaxed = relax_template(t, n_letters)
                    if relaxed is not None:
                        fixed_map_r = _build_fixed_segments(
                            relaxed, fixed_first, fixed_last
                        )
                        nf_min = sum(
                            s.min_len
                            for i, s in enumerate(relaxed.segments)
                            if i not in fixed_map_r
                        )
                        nf_max = sum(
                            s.max_len
                            for i, s in enumerate(relaxed.segments)
                            if i not in fixed_map_r
                        )
                        if nf_min <= remaining_count <= nf_max:
                            print(
                                f"Warning: Template '{template_label}' bounds"
                                f" relaxed to fit input. Results may not be"
                                f" ideal.",
                                file=sys.stderr,
                            )
                            viable.append(relaxed)

            if not viable:
                if template_label:
                    print(
                        f"Error: Template '{template_label}' cannot accommodate"
                        f" the fixed name(s) with {remaining_count}"
                        f" remaining letters.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "Error: No templates can accommodate the fixed name(s)"
                        f" with {remaining_count} remaining letters.",
                        file=sys.stderr,
                    )
                return []
            templates = viable
        else:
            # Validate explicit template against letter count (no fixed names)
            if template_label and templates:
                t = templates[0]
                if not (t.total_min() <= n_letters <= t.total_max()):
                    relaxed = relax_template(t, n_letters)
                    if relaxed is None:
                        print(
                            f"Error: Template '{template_label}' cannot work"
                            f" with {n_letters} letters (physically impossible).",
                            file=sys.stderr,
                        )
                        return []
                    print(
                        f"Warning: Template '{template_label}' is designed for"
                        f" {t.total_min()}-{t.total_max()} letters,"
                        f" but input has {n_letters}."
                        f" Results may not be ideal.",
                        file=sys.stderr,
                    )
                    templates = [relaxed]

        # Adjust attempts based on input length
        attempts_per_template = 500
        if n_letters > 20:
            attempts_per_template = 800
        if n_letters > 30:
            attempts_per_template = 1200

        all_candidates = []

        for template in templates:
            fixed_map = _build_fixed_segments(template, fixed_first, fixed_last)
            frozen = set(fixed_map.keys())

            results = solve(
                bag,
                template,
                self.model,
                n_attempts=attempts_per_template,
                fixed_segments=fixed_map or None,
            )

            for segments, _raw_score in results:
                # Skip candidates containing blocked words
                # (but respect user-provided fixed segments)
                non_fixed = [seg for i, seg in enumerate(segments) if i not in frozen]
                if any(seg in BLOCKED_WORDS for seg in non_fixed):
                    continue

                # Compute composite score on clean segments (no punctuation)
                composite = score_candidate(segments, template, self.model)

                # Apply cosmetic apostrophe after scoring (rare, skip frozen)
                display_segments = maybe_add_apostrophe(
                    segments, template, frozen_indices=frozen or None
                )

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

        # Determine which indices to ignore for overlap (fixed segments)
        # (use the first template's fixed map as representative)
        if templates:
            overlap_ignore = set(
                _build_fixed_segments(templates[0], fixed_first, fixed_last).keys()
            )
        else:
            overlap_ignore = set()

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
                overlap = _max_segment_overlap(
                    segments, final, ignore_indices=overlap_ignore or None
                )
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
