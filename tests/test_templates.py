"""Tests for templates.py - name structure templates."""

from templates import (
    NameTemplate,
    SegmentRole,
    SegmentSpec,
    format_name,
    select_templates,
)


class TestNameTemplate:
    def test_total_min(self):
        t = NameTemplate(
            "Test",
            [
                SegmentSpec(SegmentRole.FIRST, 3, 7),
                SegmentSpec(SegmentRole.LAST, 3, 8),
            ],
        )
        assert t.total_min() == 6

    def test_total_max(self):
        t = NameTemplate(
            "Test",
            [
                SegmentSpec(SegmentRole.FIRST, 3, 7),
                SegmentSpec(SegmentRole.LAST, 3, 8),
            ],
        )
        assert t.total_max() == 15


class TestSelectTemplates:
    def test_returns_templates(self):
        templates = select_templates(10)
        assert len(templates) > 0

    def test_all_viable(self):
        templates = select_templates(10)
        for t in templates:
            assert t.total_min() <= 10 <= t.total_max()

    def test_no_hyphen_for_short(self):
        templates = select_templates(8)
        for t in templates:
            roles = [s.role for s in t.segments]
            assert SegmentRole.HYPHENATED_LAST not in roles

    def test_very_short_gets_fallback(self):
        templates = select_templates(3)
        assert len(templates) >= 1

    def test_max_five_templates(self):
        templates = select_templates(12)
        assert len(templates) <= 5


class TestFormatName:
    def test_first_last(self):
        template = NameTemplate(
            "First Last",
            [
                SegmentSpec(SegmentRole.FIRST, 3, 7),
                SegmentSpec(SegmentRole.LAST, 3, 8),
            ],
        )
        result = format_name(["alice", "smith"], template)
        assert result == "Alice Smith"

    def test_initial(self):
        template = NameTemplate(
            "First M. Last",
            [
                SegmentSpec(SegmentRole.FIRST, 3, 7),
                SegmentSpec(SegmentRole.INITIAL, 1, 1),
                SegmentSpec(SegmentRole.LAST, 3, 8),
            ],
        )
        result = format_name(["alice", "m", "smith"], template)
        assert result == "Alice M. Smith"

    def test_hyphenated_last(self):
        template = NameTemplate(
            "First Last-Last",
            [
                SegmentSpec(SegmentRole.FIRST, 3, 7),
                SegmentSpec(SegmentRole.LAST, 3, 8),
                SegmentSpec(SegmentRole.HYPHENATED_LAST, 3, 8),
            ],
        )
        result = format_name(["alice", "smith", "jones"], template)
        assert result == "Alice Smith-Jones"
