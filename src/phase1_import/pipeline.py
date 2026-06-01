from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path

import emoji
import langdetect

from src.common.logging_config import setup_run_logger
from src.common.manifest import RunManifest
from src.common.pii import RedactionStats, redact_text
from src.common.run_paths import RunPaths
from src.common.run_state import RunState
from src.phase1_import.adapters.app_store import AppStoreAdapter
from src.phase1_import.adapters.play_store import PlayStoreAdapter
from src.phase1_import.adapters.base import make_content_hash
from src.phase1_import.models import CANONICAL_CSV_COLUMNS, NormalizedReview, RawReview


class ImportPipelineError(Exception):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _assign_review_id(raw: RawReview) -> str:
    if raw.review_id:
        return f"{raw.store}:{raw.review_id}"
    return f"{raw.store}:{make_content_hash(raw.store, raw.review_date, raw.rating, raw.text)}"


def _dedupe_key(review: NormalizedReview) -> str:
    return review.review_id


def merge_and_dedupe(reviews: list[NormalizedReview]) -> tuple[list[NormalizedReview], int]:
    by_key: dict[str, NormalizedReview] = {}
    removed = 0

    for review in reviews:
        key = _dedupe_key(review)
        if key not in by_key:
            by_key[key] = review
            continue
        removed += 1
        existing = by_key[key]
        if len(review.text) > len(existing.text):
            by_key[key] = review

    return list(by_key.values()), removed


def filter_date_window(
    reviews: list[NormalizedReview],
    start: date,
    end: date,
) -> tuple[list[NormalizedReview], dict[str, int]]:
    before = after = kept = 0
    filtered: list[NormalizedReview] = []

    for r in reviews:
        if r.review_date < start:
            before += 1
        elif r.review_date > end:
            after += 1
        else:
            kept += 1
            filtered.append(r)

    return filtered, {
        "before_window": before,
        "after_window": after,
        "in_window": kept,
    }


def raw_to_normalized(raw: RawReview, redaction: RedactionStats) -> tuple[NormalizedReview | None, str | None]:
    text, text_stats = redact_text(raw.text)
    title, title_stats = redact_text(raw.title)
    redaction.merge(text_stats)
    redaction.merge(title_stats)

    cleaned_text = text.strip() if text else ""
    if not cleaned_text or len(cleaned_text) < 3:
        return None, "empty_or_short"
        
    if len(cleaned_text.split()) <= 6:
        return None, "too_few_words"
        
    if emoji.emoji_count(cleaned_text) > 0:
        # Build review object anyway to preserve in emoji_reviews list
        normalized = NormalizedReview(
            review_id=_assign_review_id(raw),
            store=raw.store,
            rating=raw.rating,
            title=title,
            text=cleaned_text,
            review_date=raw.review_date,
            char_count=len(cleaned_text),
        )
        return normalized, "has_emoji"
        
    try:
        if langdetect.detect(cleaned_text) != 'en':
            return None, "non_english"
    except langdetect.LangDetectException:
        return None, "non_english"

    normalized = NormalizedReview(
        review_id=_assign_review_id(raw),
        store=raw.store,
        rating=raw.rating,
        title=title,
        text=cleaned_text,
        review_date=raw.review_date,
        char_count=len(cleaned_text),
    )
    return normalized, None


def write_normalized_csv(path: Path, reviews: list[NormalizedReview]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CANONICAL_CSV_COLUMNS)
        writer.writeheader()
        for review in sorted(reviews, key=lambda r: (r.review_date, r.review_id)):
            writer.writerow(review.to_csv_row())


def run_import(manifest: RunManifest, paths: RunPaths) -> dict:
    paths.ensure_run_dir()
    logger = setup_run_logger(paths.run_log, "phase1")

    report: dict = {
        "status": "failed",
        "week_id": manifest.week_id,
        "product": manifest.product,
        "generated_at": _utc_now(),
        "date_range": {
            "start": manifest.date_range.start.isoformat(),
            "end": manifest.date_range.end.isoformat(),
        },
        "row_counts": {},
        "redaction_counts": {},
        "errors": [],
        "warnings": [],
    }

    run_state = RunState(paths.run_state_json, manifest.week_id)
    run_state.mark_phase("import", "in_progress", current_phase="importing")

    try:
        app_adapter = AppStoreAdapter()
        play_adapter = PlayStoreAdapter()

        app_raw = app_adapter.parse_file(manifest.app_store_csv)
        play_raw = play_adapter.parse_file(manifest.play_store_csv)
        logger.info("Loaded app_store=%s play_store=%s", len(app_raw), len(play_raw))

        report["row_counts"]["app_store_raw"] = len(app_raw)
        report["row_counts"]["play_store_raw"] = len(play_raw)
        report["warnings"] = []
        if len(app_raw) == 0 and manifest.app_store_csv.exists():
            report["warnings"].append(
                "App Store CSV is empty. Add a manual App Store Connect export to "
                "reviews_raw/groww_appstore.csv (see reviews_raw/GROWW_DATA_SOURCES.md)."
            )
        if len(play_raw) == 0:
            raise ImportPipelineError(
                f"No Play Store reviews loaded from {manifest.play_store_csv}. "
                "Run: python scripts/fetch_groww_playstore.py"
            )

        total_redaction = RedactionStats()
        normalized: list[NormalizedReview] = []
        emoji_reviews: list[NormalizedReview] = []
        dropped_empty = 0
        dropped_too_short = 0
        dropped_emoji = 0
        dropped_non_english = 0

        for raw in app_raw + play_raw:
            stats = RedactionStats()
            row, reason = raw_to_normalized(raw, stats)
            total_redaction.merge(stats)
            if reason:
                if reason == "empty_or_short":
                    dropped_empty += 1
                elif reason == "too_few_words":
                    dropped_too_short += 1
                elif reason == "has_emoji":
                    dropped_emoji += 1
                    if row:
                        emoji_reviews.append(row)
                elif reason == "non_english":
                    dropped_non_english += 1
            else:
                if row:
                    normalized.append(row)

        report["row_counts"]["merged"] = len(normalized)
        report["row_counts"]["dropped_empty_text"] = dropped_empty
        report["row_counts"]["dropped_too_short"] = dropped_too_short
        report["row_counts"]["dropped_emoji"] = dropped_emoji
        report["row_counts"]["dropped_non_english"] = dropped_non_english
        report["redaction_counts"] = total_redaction.to_dict()

        deduped, dedup_removed = merge_and_dedupe(normalized)
        report["row_counts"]["dedup_removed"] = dedup_removed
        report["row_counts"]["after_dedup"] = len(deduped)

        in_window, window_stats = filter_date_window(
            deduped,
            manifest.date_range.start,
            manifest.date_range.end,
        )
        report["row_counts"].update(window_stats)
        report["row_counts"]["final"] = len(in_window)

        # Dedupe and filter emoji reviews
        emoji_deduped, _ = merge_and_dedupe(emoji_reviews)
        emoji_in_window, _ = filter_date_window(
            emoji_deduped,
            manifest.date_range.start,
            manifest.date_range.end,
        )

        if not in_window:
            report["errors"].append(
                "No reviews remain after date filter. Widen date_range in run_manifest.yaml."
            )
            raise ImportPipelineError(report["errors"][-1])

        write_normalized_csv(paths.reviews_normalized_csv, in_window)
        
        # Write to normalized.json
        normalized_data = {
            "normalized_reviews": [r.to_csv_row() for r in sorted(in_window, key=lambda r: (r.review_date, r.review_id))],
            "emoji_reviews": [r.to_csv_row() for r in sorted(emoji_in_window, key=lambda r: (r.review_date, r.review_id))]
        }
        with paths.normalized_json.open("w", encoding="utf-8") as f:
            json.dump(normalized_data, f, indent=2)
            
        logger.info("Wrote %s rows to %s", len(in_window), paths.reviews_normalized_csv)
        logger.info("Wrote %s normalized and %s emoji rows to %s", len(in_window), len(emoji_in_window), paths.normalized_json)

        if in_window:
            dates = [r.review_date for r in in_window]
            report["date_summary"] = {
                "min": min(dates).isoformat(),
                "max": max(dates).isoformat(),
            }

        report["status"] = "success"
        run_state.mark_phase("import", "complete", current_phase="theming")

    except Exception as exc:
        logger.exception("Import failed: %s", exc)
        if str(exc) not in report["errors"]:
            report["errors"].append(str(exc))
        run_state.mark_phase("import", "failed", current_phase="importing")
        raise

    finally:
        with paths.import_report_json.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    return report
