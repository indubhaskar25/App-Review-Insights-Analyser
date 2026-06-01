"""Tests for Phase 3 – Weekly Note Generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.phase3_note.pipeline import (
    build_note_payload,
    count_words,
    select_quote_candidates,
    select_top_themes,
    validate_note,
    validate_quotes_against_source,
    render_note_markdown,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def theming_report():
    """Sample theming report with 5 themes (sorted by score desc)."""
    return {
        "status": "success",
        "week_id": "2026-W20",
        "product": "Groww",
        "analytics": {
            "themes": {
                "support": {
                    "name": "Support & Service",
                    "review_count": 148,
                    "avg_rating": 1.46,
                    "low_rating_pct": 84.5,
                    "theme_score": 0.4977,
                },
                "investments": {
                    "name": "Mutual Funds & Investments",
                    "review_count": 327,
                    "avg_rating": 3.0,
                    "low_rating_pct": 44.6,
                    "theme_score": 0.407,
                },
                "payments": {
                    "name": "Payments & Transactions",
                    "review_count": 52,
                    "avg_rating": 2.19,
                    "low_rating_pct": 63.5,
                    "theme_score": 0.3833,
                },
                "onboarding": {
                    "name": "KYC & Verification",
                    "review_count": 21,
                    "avg_rating": 2.62,
                    "low_rating_pct": 61.9,
                    "theme_score": 0.3341,
                },
                "stability": {
                    "name": "App Stability & UX",
                    "review_count": 281,
                    "avg_rating": 3.67,
                    "low_rating_pct": 30.2,
                    "theme_score": 0.3229,
                },
            },
            "unmatched_count": 5,
            "representative_quotes": {
                "support": [
                    {
                        "text": "the charges are so heavy and the customer care also bad",
                        "review_id": "play_store:abc123",
                        "rating": 1,
                        "confidence": 1.0,
                    },
                ],
                "investments": [
                    {
                        "text": "many indicator not apply on chart",
                        "review_id": "play_store:def456",
                        "rating": 1,
                        "confidence": 1.0,
                    },
                ],
                "payments": [
                    {
                        "text": "silently deducting brokerage charge even if the transaction is unsuccessful",
                        "review_id": "play_store:ghi789",
                        "rating": 1,
                        "confidence": 1.0,
                    },
                ],
            },
        },
    }


@pytest.fixture
def themed_reviews():
    """Sample themed reviews."""
    return [
        {
            "review_id": "play_store:abc123",
            "store": "play_store",
            "rating": 1,
            "text": "the charges are so heavy and the customer care also bad",
            "theme_id": "support",
            "confidence": 1.0,
            "representative_quote": "the charges are so heavy and the customer care also bad",
        },
        {
            "review_id": "play_store:def456",
            "store": "play_store",
            "rating": 1,
            "text": "many indicator not apply on chart something application not working",
            "theme_id": "investments",
            "confidence": 1.0,
            "representative_quote": "many indicator not apply on chart",
        },
        {
            "review_id": "play_store:ghi789",
            "store": "play_store",
            "rating": 1,
            "text": "this app silently deducting brokerage charge even if the transaction is unsuccessful",
            "theme_id": "payments",
            "confidence": 1.0,
            "representative_quote": "silently deducting brokerage charge even if the transaction is unsuccessful",
        },
        {
            "review_id": "play_store:jkl012",
            "store": "play_store",
            "rating": 2,
            "text": "app freezes during market volatility",
            "theme_id": "stability",
            "confidence": 0.9,
            "representative_quote": "app freezes during market volatility",
        },
    ]


# ---------------------------------------------------------------------------
# Test: count_words
# ---------------------------------------------------------------------------

class TestCountWords:
    def test_empty(self):
        assert count_words("") == 0

    def test_single_word(self):
        assert count_words("hello") == 1

    def test_multiple_words(self):
        assert count_words("the quick brown fox") == 4

    def test_extra_whitespace(self):
        assert count_words("  hello   world  ") == 2


# ---------------------------------------------------------------------------
# Test: select_top_themes
# ---------------------------------------------------------------------------

class TestSelectTopThemes:
    def test_selects_top_3(self, theming_report):
        top = select_top_themes(theming_report, n=3)
        assert len(top) == 3
        assert top[0]["id"] == "support"
        assert top[0]["theme_score"] == 0.4977
        assert top[1]["id"] == "investments"
        assert top[2]["id"] == "payments"

    def test_selects_top_2(self, theming_report):
        top = select_top_themes(theming_report, n=2)
        assert len(top) == 2
        assert top[0]["id"] == "support"
        assert top[1]["id"] == "investments"

    def test_selects_all_if_fewer(self):
        report = {"analytics": {"themes": {
            "a": {"name": "A", "review_count": 10, "avg_rating": 2.0, "low_rating_pct": 50, "theme_score": 0.5},
        }}}
        top = select_top_themes(report, n=3)
        assert len(top) == 1

    def test_raises_on_empty(self):
        with pytest.raises(RuntimeError, match="No theme analytics"):
            select_top_themes({"analytics": {"themes": {}}}, n=3)

    def test_preserves_theme_metadata(self, theming_report):
        top = select_top_themes(theming_report, n=1)
        t = top[0]
        assert t["name"] == "Support & Service"
        assert t["review_count"] == 148
        assert t["avg_rating"] == 1.46
        assert t["low_rating_pct"] == 84.5


# ---------------------------------------------------------------------------
# Test: select_quote_candidates
# ---------------------------------------------------------------------------

class TestSelectQuoteCandidates:
    def test_selects_from_precomputed(self, theming_report, themed_reviews):
        top_ids = ["support", "investments", "payments"]
        result = select_quote_candidates(theming_report, themed_reviews, top_ids)
        assert "support" in result
        assert len(result["support"]) >= 1
        assert result["support"][0]["text"] == "the charges are so heavy and the customer care also bad"
        assert result["support"][0]["source_review_id"] == "play_store:abc123"

    def test_fallback_to_themed_reviews(self, themed_reviews):
        """When no pre-computed quotes, fall back to themed_reviews."""
        report = {"analytics": {"themes": {}, "representative_quotes": {}}}
        top_ids = ["support"]
        result = select_quote_candidates(report, themed_reviews, top_ids)
        assert len(result["support"]) >= 1
        assert result["support"][0]["theme_id"] == "support"

    def test_pii_quotes_skipped(self, theming_report, themed_reviews):
        """Quotes with PII should be skipped."""
        report = {
            "analytics": {
                "themes": {},
                "representative_quotes": {
                    "support": [{
                        "text": "email me at user@example.com for details",
                        "review_id": "play_store:pii1",
                        "rating": 1,
                        "confidence": 0.9,
                    }],
                },
            },
        }
        top_ids = ["support"]
        result = select_quote_candidates(report, themed_reviews, top_ids)
        # Should fall back to themed_reviews since PII quote is skipped
        for q in result.get("support", []):
            assert "user@example.com" not in q["text"]

    def test_prefers_low_rated(self, theming_report, themed_reviews):
        """Candidates should be sorted by rating (low first)."""
        top_ids = ["support"]
        result = select_quote_candidates(theming_report, themed_reviews, top_ids)
        if len(result.get("support", [])) > 1:
            ratings = [q["rating"] for q in result["support"]]
            assert ratings == sorted(ratings)


# ---------------------------------------------------------------------------
# Test: validate_note
# ---------------------------------------------------------------------------

class TestValidateNote:
    def test_valid_note(self, themed_reviews):
        note = {
            "top_themes": [
                {"id": "support", "name": "Support", "summary": "Bad service"},
                {"id": "investments", "name": "Investments", "summary": "Chart issues"},
                {"id": "payments", "name": "Payments", "summary": "Hidden charges"},
            ],
            "quotes": [
                {"text": "bad service", "theme_id": "support", "source_review_id": "play_store:abc123"},
                {"text": "chart issues", "theme_id": "investments", "source_review_id": "play_store:def456"},
                {"text": "hidden charges", "theme_id": "payments", "source_review_id": "play_store:ghi789"},
            ],
            "action_ideas": [
                {"text": "Fix support", "theme_id": "support"},
                {"text": "Fix charts", "theme_id": "investments"},
                {"text": "Fix charges", "theme_id": "payments"},
            ],
            "body_markdown": "Short note body under limit",
        }
        issues = validate_note(note, themed_reviews)
        assert issues == []

    def test_wrong_theme_count(self, themed_reviews):
        note = {
            "top_themes": [{"id": "a", "name": "A", "summary": "x"}],
            "quotes": [{"text": "q", "theme_id": "a", "source_review_id": "play_store:abc123"}],
            "action_ideas": [{"text": "act", "theme_id": "a"}],
            "body_markdown": "ok",
        }
        issues = validate_note(note, themed_reviews)
        assert any("3 top_themes" in i for i in issues)

    def test_over_word_limit(self, themed_reviews):
        note = {
            "top_themes": [{"id": f"t{i}", "name": f"T{i}", "summary": "x"} for i in range(3)],
            "quotes": [{"text": "q", "theme_id": "t0", "source_review_id": ""} for _ in range(3)],
            "action_ideas": [{"text": "a", "theme_id": "t0"} for _ in range(3)],
            "body_markdown": " ".join(["word"] * 300),
        }
        issues = validate_note(note, themed_reviews)
        assert any("words" in i for i in issues)

    def test_pii_in_body(self, themed_reviews):
        note = {
            "top_themes": [{"id": f"t{i}", "name": f"T{i}", "summary": "x"} for i in range(3)],
            "quotes": [{"text": "q", "theme_id": "t0", "source_review_id": ""} for _ in range(3)],
            "action_ideas": [{"text": "a", "theme_id": "t0"} for _ in range(3)],
            "body_markdown": "Contact user@example.com for details",
        }
        issues = validate_note(note, themed_reviews)
        assert any("PII" in i for i in issues)

    def test_unknown_review_id(self, themed_reviews):
        note = {
            "top_themes": [{"id": f"t{i}", "name": f"T{i}", "summary": "x"} for i in range(3)],
            "quotes": [
                {"text": "q", "theme_id": "t0", "source_review_id": "nonexistent_id"},
            ] + [{"text": "q", "theme_id": "t0", "source_review_id": ""} for _ in range(2)],
            "action_ideas": [{"text": "a", "theme_id": "t0"} for _ in range(3)],
            "body_markdown": "ok",
        }
        issues = validate_note(note, themed_reviews)
        assert any("unknown review_id" in i for i in issues)


# ---------------------------------------------------------------------------
# Test: validate_quotes_against_source
# ---------------------------------------------------------------------------

class TestValidateQuotesAgainstSource:
    def test_verbatim_match(self, themed_reviews):
        quotes = [
            {"text": "the charges are so heavy and the customer care also bad", "source_review_id": "play_store:abc123"},
        ]
        issues = validate_quotes_against_source(quotes, themed_reviews)
        assert issues == []

    def test_non_verbatim_fails(self, themed_reviews):
        quotes = [
            {"text": "charges are heavy and customer care is terrible", "source_review_id": "play_store:abc123"},
        ]
        issues = validate_quotes_against_source(quotes, themed_reviews)
        assert len(issues) > 0

    def test_missing_source_id(self, themed_reviews):
        quotes = [
            {"text": "some text", "source_review_id": "nonexistent"},
        ]
        # Should not crash, just skip
        issues = validate_quotes_against_source(quotes, themed_reviews)
        # No issue since review not found (already flagged by validate_note)
        assert issues == []


# ---------------------------------------------------------------------------
# Test: build_note_payload
# ---------------------------------------------------------------------------

class TestBuildNotePayload:
    def test_payload_structure(self, theming_report, themed_reviews):
        top_themes = select_top_themes(theming_report, n=3)
        top_ids = [t["id"] for t in top_themes]
        quotes = select_quote_candidates(theming_report, themed_reviews, top_ids)

        payload = build_note_payload(top_themes, quotes, "Groww", "2026-W20")

        assert payload["product"] == "Groww"
        assert payload["week_id"] == "2026-W20"
        assert len(payload["top_themes"]) == 3
        assert payload["constraints"]["max_words"] == 250
        assert payload["constraints"]["num_themes"] == 3
        assert payload["constraints"]["num_quotes"] == 3
        assert payload["constraints"]["num_actions"] == 3


# ---------------------------------------------------------------------------
# Test: render_note_markdown
# ---------------------------------------------------------------------------

class TestRenderNoteMarkdown:
    def test_uses_body_markdown_if_present(self):
        note = {"body_markdown": "# My Custom Note\n\nHello world"}
        md = render_note_markdown(note, "Groww", "2026-W20")
        assert md == "# My Custom Note\n\nHello world"

    def test_reconstructs_from_fields(self):
        note = {
            "top_themes": [
                {"id": "support", "name": "Support & Service", "summary": "Bad service"},
            ],
            "quotes": [
                {"text": "terrible support", "theme_id": "support", "source_review_id": "r1"},
            ],
            "action_ideas": [
                {"text": "Improve support response time", "theme_id": "support"},
            ],
        }
        md = render_note_markdown(note, "Groww", "2026-W20")
        assert "Weekly Review Pulse" in md
        assert "Support & Service" in md
        assert "terrible support" in md
        assert "Improve support response time" in md
