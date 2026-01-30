"""Integration tests - end-to-end anagram generation and verification."""

import random

from anagrammer import verify_anagram
from generator import AnagramGenerator
from letterbag import LetterBag
from util import normalize


class TestVerifyAnagram:
    def test_valid_anagram(self):
        assert verify_anagram("listen", "Silent")

    def test_invalid_anagram(self):
        assert not verify_anagram("hello", "world")

    def test_ignores_spaces_and_case(self):
        assert verify_anagram("William Shakespeare", "I am a weakish speller")

    def test_ignores_punctuation(self):
        assert verify_anagram("abc", "A.B.C.")


class TestEndToEnd:
    """Integration tests that run the full generation pipeline."""

    def test_generates_results(self):
        random.seed(42)
        gen = AnagramGenerator(dataset="both")
        results = gen.generate("William Shakespeare", n_results=5)
        assert len(results) > 0

    def test_all_results_are_perfect_anagrams(self):
        """The core invariant: every result uses exactly the input letters."""
        random.seed(42)
        gen = AnagramGenerator(dataset="both")
        phrase = "Hello World"
        results = gen.generate(phrase, n_results=5)
        normalized_input = normalize(phrase)
        input_bag = LetterBag(normalized_input)

        for name, _score, _label, _segments in results:
            result_bag = LetterBag(name)
            assert result_bag == input_bag, (
                f"Anagram mismatch: '{name}' is not a perfect anagram of '{phrase}'"
            )

    def test_results_have_expected_shape(self):
        random.seed(42)
        gen = AnagramGenerator(dataset="both")
        results = gen.generate("Testing", n_results=3)
        for name, score, label, segments in results:
            assert isinstance(name, str)
            assert isinstance(score, float)
            assert isinstance(label, str)
            assert isinstance(segments, list)

    def test_short_input_returns_empty(self):
        gen = AnagramGenerator(dataset="both")
        results = gen.generate("ab", n_results=5)
        assert results == []

    def test_seed_reproducibility(self):
        gen = AnagramGenerator(dataset="both")
        random.seed(42)
        r1 = gen.generate("Reproducible", n_results=5)
        random.seed(42)
        r2 = gen.generate("Reproducible", n_results=5)
        names1 = [name for name, *_ in r1]
        names2 = [name for name, *_ in r2]
        assert names1 == names2

    def test_female_dataset(self):
        random.seed(42)
        gen = AnagramGenerator(dataset="female")
        results = gen.generate("Dragon Fire", n_results=3)
        assert len(results) > 0
        # Verify anagram property for female dataset too
        input_bag = LetterBag(normalize("Dragon Fire"))
        for name, _score, _label, _segments in results:
            assert LetterBag(name) == input_bag

    def test_male_dataset(self):
        random.seed(42)
        gen = AnagramGenerator(dataset="male")
        results = gen.generate("Dragon Fire", n_results=3)
        assert len(results) > 0
        input_bag = LetterBag(normalize("Dragon Fire"))
        for name, _score, _label, _segments in results:
            assert LetterBag(name) == input_bag
