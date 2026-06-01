#!/usr/bin/env python3
"""Update run_manifest.yaml with a new week_id and date range.

Used by GitHub Actions to dynamically configure each weekly run
without manual edits. Safe to run locally too.

Usage:
    python scripts/update_manifest.py \
        --week-id 2026-W22 \
        --start-date 2026-03-02 \
        --end-date 2026-05-25
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "config" / "run_manifest.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="Update run manifest for a new week")
    parser.add_argument("--week-id", required=True, help="ISO week id, e.g. 2026-W22")
    parser.add_argument("--start-date", required=True, help="Window start (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="Window end (YYYY-MM-DD)")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST,
        help="Path to run_manifest.yaml",
    )
    args = parser.parse_args()

    path = args.manifest
    if not path.exists():
        print(f"ERROR: manifest not found at {path}", file=sys.stderr)
        return 1

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Update fields
    data["week_id"] = args.week_id
    data["date_range"]["start"] = args.start_date
    data["date_range"]["end"] = args.end_date
    data["outputs"]["run_dir"] = f"data/runs/{args.week_id}"

    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Manifest updated: week_id={args.week_id}  window={args.start_date} → {args.end_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
