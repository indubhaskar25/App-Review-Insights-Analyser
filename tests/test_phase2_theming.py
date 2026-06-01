"""Tests for Phase 2 – Theme Grouping pipeline.

Covers: preprocessing, validation, analytics, theme scoring, quote extraction.
LLM calls are mocked – no real API keys needed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.common.manifest import DateRange, LLMConfig, RunManifest, ThemingConfig
from src.common.run_paths import RunPaths
from src.phase2_theming.pipeline import (
    THEME_SCORE_WEIGHTS,
    _closest_theme,
    compute_theme_analytics,
    extract_representative_quotes,
    preprocess_reviews,
    truncate_text,
    validate_classifications,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LEGEND = [
    {"id": "payments", "name": "Payments & Transactions", "example_keywords": ["upi", "withdraw"]},
    {"id": "onboarding", "name": "KYC & Verification", "example_keywords": ["kyc", "signup"]},
    {"id": "stability", "name": "App Stability & UX", "example_keywords": ["crash", "slow"]},
    {"id": "investments", "name": "Mutual Funds & Investments", "example_keywords": ["sip", "mutual fund"]},
    {"id": "support", "name": "Support & Service", "example_keywords": ["support", "help"]},
]

SAMPLE_REVIEWS = [
    {"review_id": "r1", "store": "play_store", "rating": 1, "title": "",
     "text": "UPI transfer failed, money deducted but not credited", "review_date": "2026-05-15"},
    {"review_id": "r2", "store": "play_store", "rating": 2, "title": "",
     "text": "KYC is taking too long, documents rejected multiple times without reason", "review_date": "2026-05-14"},
    {"review_id": "r3", "store": "play_store", "rating": 1, "title": "",
     "text": "App crashes every time I open the portfolio page", "review_date": "2026-05-13"},
    {"review_id": "r4", "store": "play_store", "rating": 3, "title": "",
     "text": "SIP investment is good but the mutual fund section needs improvement", "review_date": "2026-05-10"},
    {"review_id": "r5", "store": "play_store", "rating": 2, "title": "",
     "text": "Customer support is unresponsive, no reply to my ticket for 5 days", "review_date": "2026-05-08"},
    {"review_id": "r6", "store": "play_store", "rating": 5, "title": "",
     "text": "Very good app, been using for 3 years, excellent for trading", "review_date": "2026-05-12"},
    {"review_id": "r7", "store": "play_store", "rating": 1, "title": "",
     "text": "Withdrawal pending for 7 days, worst experience with payments", "review_date": "2026-05-16"},
]


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestTruncateText(unittest.TestCase):
    def test_short_text_unchanged(self) -> None:
        self.assertEqual(truncate_text("hello world", 40), "hello world")

    def test_exact_limit(self) -> None:
        text = " ".join(["word"] * 40)
        self.assertEqual(truncate_text(text, 40), text)

    def test_truncated(self) -> None:
        text = " ".join(["word"] * 50)
        result = truncate_text(text, 40)
        self.assertEqual(len(result.split()), 40)

    def test_empty_text(self) -> None:
        self.assertEqual(truncate_text("", 40), "")


class TestPreprocessReviews(unittest.TestCase):
    def test_limits_reviews(self) -> None:
        reviews = SAMPLE_REVIEWS.copy()
        result, stats = preprocess_reviews(reviews, review_limit=3)
        self.assertEqual(len(result), 3)
        self.assertEqual(stats["after_limit"], 3)
        self.assertEqual(stats["input_count"], 7)

    def test_sorts_by_date_latest_first(self) -> None:
        result, _ = preprocess_reviews(SAMPLE_REVIEWS, review_limit=100)
        dates = [r["review_date"] for r in result]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_truncation(self) -> None:
        long_review = [{"review_id": "x", "text": " ".join(["word"] * 100), "review_date": "2026-05-01"}]
        result, stats = preprocess_reviews(long_review, review_limit=100, truncation_words=40)
        self.assertEqual(stats["truncated_count"], 1)
        self.assertEqual(len(result[0]["_text_classify"].split()), 40)
        # Full text preserved
        self.assertEqual(len(result[0]["_text_full"].split()), 100)

    def test_no_truncation_needed(self) -> None:
        short_review = [{"review_id": "x", "text": "short review", "review_date": "2026-05-01"}]
        result, stats = preprocess_reviews(short_review, review_limit=100, truncation_words=40)
        self.assertEqual(stats["truncated_count"], 0)


class TestValidateClassifications(unittest.TestCase):
    def test_known_themes_pass(self) -> None:
        classifications = [
            {"review_id": "r1", "theme_id": "payments", "confidence": 0.9},
            {"review_id": "r2", "theme_id": "stability", "confidence": 0.8},
        ]
        validated, merge_log = validate_classifications(classifications, SAMPLE_LEGEND)
        self.assertEqual(len(merge_log), 0)
        self.assertEqual(validated[0]["theme_id"], "payments")

    def test_unknown_theme_mapped(self) -> None:
        classifications = [
            {"review_id": "r1", "theme_id": "transaction_issues", "confidence": 0.7},
        ]
        validated, merge_log = validate_classifications(classifications, SAMPLE_LEGEND)
        self.assertEqual(len(merge_log), 1)
        self.assertNotEqual(validated[0]["theme_id"], "transaction_issues")

    def test_unassigned_preserved(self) -> None:
        classifications = [
            {"review_id": "r1", "theme_id": "unassigned", "confidence": 0.0},
        ]
        validated, merge_log = validate_classifications(classifications, SAMPLE_LEGEND)
        self.assertEqual(validated[0]["theme_id"], "unassigned")
        self.assertEqual(len(merge_log), 0)


class TestClosestTheme(unittest.TestCase):
    def test_exact_keyword_match(self) -> None:
        result = _closest_theme("payment_issues", SAMPLE_LEGEND)
        self.assertEqual(result, "payments")

    def test_no_match_returns_unassigned(self) -> None:
        result = _closest_theme("xyz_random_abc", SAMPLE_LEGEND)
        self.assertEqual(result, "unassigned")


class TestComputeThemeAnalytics(unittest.TestCase):
    def test_basic_analytics(self) -> None:
        themed = [
            {"review_id": "r1", "theme_id": "payments", "rating": 1, "confidence": 0.9,
             "review_date": "2026-05-15", "text": "UPI failed"},
            {"review_id": "r2", "theme_id": "payments", "rating": 2, "confidence": 0.8,
             "review_date": "2026-05-14", "text": "Withdrawal stuck"},
            {"review_id": "r3", "theme_id": "stability", "rating": 1, "confidence": 0.9,
             "review_date": "2026-05-13", "text": "App crash"},
            {"review_id": "r4", "theme_id": "unassigned", "rating": 3, "confidence": 0.0,
             "review_date": "2026-05-01", "text": "Meh"},
        ]
        analytics = compute_theme_analytics(themed, total_reviews=4, legend_themes=SAMPLE_LEGEND)

        self.assertIn("payments", analytics["themes"])
        self.assertIn("stability", analytics["themes"])
        self.assertEqual(analytics["themes"]["payments"]["review_count"], 2)
        self.assertEqual(analytics["themes"]["payments"]["avg_rating"], 1.5)
        self.assertEqual(analytics["unmatched_count"], 1)

    def test_theme_score_ordering(self) -> None:
        """Theme with more volume + lower ratings should score higher."""
        themed = [
            {"review_id": f"r{i}", "theme_id": "payments", "rating": 1,
             "confidence": 0.9, "review_date": "2026-05-15", "text": "t"}
            for i in range(10)
        ] + [
            {"review_id": f"s{i}", "theme_id": "stability", "rating": 5,
             "confidence": 0.9, "review_date": "2026-05-10", "text": "t"}
            for i in range(3)
        ]
        analytics = compute_theme_analytics(themed, total_reviews=13, legend_themes=SAMPLE_LEGEND)
        # payments (10 reviews, all 1★) should score higher than stability (3 reviews, all 5★)
        self.assertGreater(
            analytics["themes"]["payments"]["theme_score"],
            analytics["themes"]["stability"]["theme_score"],
        )

    def test_low_rating_percentage(self) -> None:
        themed = [
            {"review_id": "r1", "theme_id": "payments", "rating": 1, "confidence": 0.9,
             "review_date": "2026-05-15", "text": "t"},
            {"review_id": "r2", "theme_id": "payments", "rating": 2, "confidence": 0.8,
             "review_date": "2026-05-14", "text": "t"},
            {"review_id": "r3", "theme_id": "payments", "rating": 5, "confidence": 0.7,
             "review_date": "2026-05-13", "text": "t"},
        ]
        analytics = compute_theme_analytics(themed, total_reviews=3, legend_themes=SAMPLE_LEGEND)
        # 2 out of 3 are ≤2★ = 66.7%
        self.assertAlmostEqual(analytics["themes"]["payments"]["low_rating_pct"], 66.7, places=0)


class TestExtractRepresentativeQuotes(unittest.TestCase):
    def test_extracts_quotes(self) -> None:
        themed = [
            {"review_id": "r1", "theme_id": "payments", "rating": 1, "confidence": 0.9,
             "representative_quote": "UPI transfer failed", "_text_full": "UPI transfer failed again"},
            {"review_id": "r2", "theme_id": "payments", "rating": 2, "confidence": 0.8,
             "representative_quote": "withdrawal stuck", "_text_full": "My withdrawal stuck for days"},
        ]
        quotes = extract_representative_quotes(themed, "payments")
        self.assertEqual(len(quotes), 2)
        self.assertEqual(quotes[0]["text"], "UPI transfer failed")

    def test_skips_pii_quotes(self) -> None:
        themed = [
            {"review_id": "r1", "theme_id": "payments", "rating": 1, "confidence": 0.9,
             "representative_quote": "call me at 9876543210", "_text_full": "call me at 9876543210"},
        ]
        quotes = extract_representative_quotes(themed, "payments")
        self.assertEqual(len(quotes), 0)

    def test_max_quotes_limit(self) -> None:
        themed = [
            {"review_id": f"r{i}", "theme_id": "payments", "rating": 1,
             "confidence": 0.9, "representative_quote": f"quote {i}",
             "_text_full": f"quote {i}"}
            for i in range(5)
        ]
        quotes = extract_representative_quotes(themed, "payments", max_quotes=3)
        self.assertEqual(len(quotes), 3)


class TestManifestDualModel(unittest.TestCase):
    def test_effective_classification_model(self) -> None:
        llm = LLMConfig(
            provider="groq", model="llama-3.3-70b-versatile", temperature=0.3,
            model_classification="llama-3.1-8b-instant",
        )
        self.assertEqual(llm.effective_classification_model, "llama-3.1-8b-instant")

    def test_fallback_to_model(self) -> None:
        llm = LLMConfig(provider="groq", model="llama-3.3-70b-versatile", temperature=0.3)
        self.assertEqual(llm.effective_classification_model, "llama-3.3-70b-versatile")
        self.assertEqual(llm.effective_summary_model, "llama-3.3-70b-versatile")


if __name__ == "__main__":
    unittest.main()
