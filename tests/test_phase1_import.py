from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.common.manifest import RunManifest, DateRange
from src.common.pii import redact_text, scan_for_pii
from src.common.run_paths import RunPaths
from src.phase1_import.adapters.app_store import AppStoreAdapter
from src.phase1_import.adapters.play_store import PlayStoreAdapter
from src.phase1_import.pipeline import filter_date_window, merge_and_dedupe, run_import
from src.phase1_import.models import NormalizedReview


FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent


class TestAppStoreAdapter(unittest.TestCase):
    def test_maps_columns(self) -> None:
        adapter = AppStoreAdapter()
        reviews = adapter.parse_file(FIXTURES / "app_store_sample.csv")
        self.assertEqual(len(reviews), 3)
        self.assertEqual(reviews[0].store, "app_store")
        self.assertEqual(reviews[0].rating, 2)
        self.assertIn("user@mail.com", reviews[0].text)


class TestPlayStoreAdapter(unittest.TestCase):
    def test_maps_columns(self) -> None:
        adapter = PlayStoreAdapter()
        reviews = adapter.parse_file(FIXTURES / "play_store_sample.csv")
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0].store, "play_store")
        self.assertEqual(reviews[0].rating, 1)


class TestPII(unittest.TestCase):
    def test_redact_email(self) -> None:
        text, stats = redact_text("Email me at user@mail.com please")
        self.assertNotIn("user@mail.com", text)
        self.assertIn("[REDACTED]", text)
        self.assertEqual(stats.emails, 1)

    def test_scan_clean(self) -> None:
        text, _ = redact_text("No contact info here")
        self.assertEqual(scan_for_pii(text), [])


class TestPipelineHelpers(unittest.TestCase):
    def test_date_filter(self) -> None:
        reviews = [
            NormalizedReview("a", "app_store", 5, "", "ok", date(2026, 1, 1)),
            NormalizedReview("b", "app_store", 5, "", "ok", date(2026, 3, 15)),
        ]
        kept, stats = filter_date_window(reviews, date(2026, 2, 1), date(2026, 5, 1))
        self.assertEqual(len(kept), 1)
        self.assertEqual(stats["before_window"], 1)

    def test_dedup_keeps_longer_text(self) -> None:
        reviews = [
            NormalizedReview("x", "play_store", 1, "", "short", date(2026, 4, 1)),
            NormalizedReview("x", "play_store", 1, "", "much longer text", date(2026, 4, 1)),
        ]
        merged, removed = merge_and_dedupe(reviews)
        self.assertEqual(removed, 1)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].text, "much longer text")

    def test_empty_text_dropped_in_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app_csv = ROOT / "reviews_raw" / "sample" / "appstore_sample.csv"
            play_csv = ROOT / "reviews_raw" / "sample" / "playstore_sample.csv"
            run_dir = tmp_path / "runs" / "2026-W20"
            manifest = RunManifest(
                product="TestApp",
                week_id="2026-W20",
                date_range=DateRange(date(2026, 2, 24), date(2026, 5, 18)),
                app_store_csv=app_csv,
                play_store_csv=play_csv,
                run_dir=run_dir,
                email_to="test@example.com",
                email_subject_template="[Weekly Pulse] {product} — {week_id}",
                docs_title_template="{product} — Weekly Review Pulse — {week_id}",
            )
            paths = RunPaths("2026-W20", run_dir)
            report = run_import(manifest, paths)
            self.assertEqual(report["status"], "success")
            self.assertGreater(report["row_counts"]["final"], 0)
            self.assertGreater(report["row_counts"]["dropped_empty_text"], 0)
            with paths.import_report_json.open() as f:
                saved = json.load(f)
            self.assertEqual(saved["status"], "success")


if __name__ == "__main__":
    unittest.main()
