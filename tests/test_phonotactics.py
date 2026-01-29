"""Tests for phonotactics.py - pronounceability constraints."""

from phonotactics import (
    get_coda,
    get_onset,
    is_valid_coda,
    is_valid_onset,
    is_valid_segment,
    phonotactic_filter,
)


class TestGetOnset:
    def test_consonant_start(self):
        assert get_onset("bran") == "br"

    def test_vowel_start(self):
        assert get_onset("art") == ""

    def test_single_consonant(self):
        assert get_onset("tan") == "t"

    def test_all_consonants(self):
        assert get_onset("brst") == "brst"


class TestGetCoda:
    def test_consonant_end(self):
        assert get_coda("mist") == "st"

    def test_vowel_end(self):
        assert get_coda("tree") == ""

    def test_single_consonant(self):
        assert get_coda("bat") == "t"


class TestIsValidOnset:
    def test_single_consonant_always_valid(self):
        assert is_valid_onset("t")
        assert is_valid_onset("b")

    def test_empty_valid(self):
        assert is_valid_onset("")

    def test_valid_two_letter(self):
        assert is_valid_onset("bl")
        assert is_valid_onset("ch")
        assert is_valid_onset("str"[:2])  # "st"

    def test_invalid_two_letter(self):
        assert not is_valid_onset("zx")
        assert not is_valid_onset("bk")

    def test_valid_three_letter(self):
        assert is_valid_onset("str")
        assert is_valid_onset("spl")

    def test_too_long(self):
        assert not is_valid_onset("strb")


class TestIsValidCoda:
    def test_single_consonant_always_valid(self):
        assert is_valid_coda("t")

    def test_valid_two_letter(self):
        assert is_valid_coda("st")
        assert is_valid_coda("ng")

    def test_invalid_two_letter(self):
        assert not is_valid_coda("zx")

    def test_valid_three_letter(self):
        assert is_valid_coda("nch")
        assert is_valid_coda("rst")


class TestIsValidSegment:
    def test_empty_invalid(self):
        assert not is_valid_segment("")

    def test_single_letter_valid(self):
        assert is_valid_segment("a")
        assert is_valid_segment("b")

    def test_common_names(self):
        assert is_valid_segment("mark")
        assert is_valid_segment("alice")
        assert is_valid_segment("beth")

    def test_must_have_vowel(self):
        assert not is_valid_segment("bcd")

    def test_bad_onset(self):
        assert not is_valid_segment("bkale")

    def test_bad_coda(self):
        assert not is_valid_segment("mabzx")

    def test_excessive_consonants(self):
        # 4+ consecutive consonants is rejected
        assert not is_valid_segment("abstrd")

    def test_invalid_vowel_pair(self):
        # "uu" is not in VALID_VOWEL_PAIRS
        assert not is_valid_segment("buun")


class TestPhonotacticFilter:
    def test_filters_bad_consonant_run(self):
        # If partial is "abst" (3 trailing consonants), adding another consonant
        # would make 4 which should be filtered
        candidates = [("r", -1.0), ("a", -2.0)]
        result = phonotactic_filter(candidates, "abst", 4, 6)
        chars = [c for c, _ in result]
        assert "r" not in chars
        assert "a" in chars

    def test_allows_valid_additions(self):
        candidates = [("a", -1.0), ("e", -2.0)]
        result = phonotactic_filter(candidates, "br", 2, 5)
        assert len(result) == 2
