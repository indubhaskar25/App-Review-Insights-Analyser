#!/usr/bin/env python3
"""
Fetch public Groww Play Store reviews into reviews_raw/groww_playstore.csv.

Educational/portfolio use only. Not affiliated with Groww.
Requires: pip install google-play-scraper pyyaml
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.common.manifest import load_manifest

APP_ID = "com.nextbillion.groww"
OUTPUT = ROOT / "reviews_raw" / "groww_playstore.csv"


def main() -> int:
    try:
        from google_play_scraper import Sort, reviews
    except ImportError:
        print("Install: pip install google-play-scraper", file=sys.stderr)
        return 1

    manifest = load_manifest(ROOT / "config" / "run_manifest.yaml", ROOT)
    start = datetime.combine(manifest.date_range.start, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(manifest.date_range.end, datetime.max.time(), tzinfo=timezone.utc)

    all_reviews: list = []
    token = None
    for i in range(60):
        batch, token = reviews(
            APP_ID,
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=200,
            continuation_token=token,
        )
        if not batch:
            break
        all_reviews.extend(batch)
        oldest = min(r["at"] for r in batch)
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        print(f"batch {i + 1}: total={len(all_reviews)} oldest={oldest.date()}")
        if oldest < start:
            break
        if not token:
            break

    rows = []
    seen: set[str] = set()
    for r in all_reviews:
        at = r["at"]
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        if not (start <= at <= end):
            continue
        text = (r.get("content") or "").strip()
        if not text:
            continue
        rid = r.get("reviewId") or f"ps_{at.isoformat()}"
        if rid in seen:
            continue
        seen.add(rid)
        rows.append(
            {
                "Review ID": rid,
                "Review Submit Date": at.strftime("%Y-%m-%d"),
                "Star Rating": r.get("score", ""),
                "Review Title": "",
                "Review Text": text.replace("\n", " "),
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Review ID",
                "Review Submit Date",
                "Star Rating",
                "Review Title",
                "Review Text",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} reviews to {OUTPUT}")
    if rows:
        dates = [r["Review Submit Date"] for r in rows]
        print(f"Date range: {min(dates)} → {max(dates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
