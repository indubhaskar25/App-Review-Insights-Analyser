"""Phase 2 – Theme Grouping CLI

Usage:
    python -m src.phase2_theming --manifest config/run_manifest.yaml
    python -m src.phase2_theming --week-id 2026-W20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.common.logging_config import setup_run_logger
from src.common.manifest import load_manifest
from src.common.run_paths import RunPaths, get_project_root
from src.phase2_theming.pipeline import run_theming


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Phase 2: Theme Grouping")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to run_manifest.yaml (default: config/run_manifest.yaml)",
    )
    parser.add_argument(
        "--week-id",
        type=str,
        default=None,
        help="Override week_id from manifest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run preprocessing only (no LLM calls)",
    )
    args = parser.parse_args(argv)

    root = get_project_root()
    manifest_path = args.manifest or root / "config" / "run_manifest.yaml"
    manifest = load_manifest(manifest_path, root)

    if args.week_id:
        manifest.week_id = args.week_id
        manifest.run_dir = root / "data" / "runs" / args.week_id

    paths = RunPaths.from_manifest_run_dir(manifest.run_dir, manifest.week_id)

    # Setup logger
    logger = setup_run_logger(paths.run_log, "phase2")

    logger.info(
        "Phase 2 starting: product=%s week_id=%s model=%s batch_size=%d",
        manifest.product,
        manifest.week_id,
        manifest.llm.effective_classification_model if manifest.llm else "N/A",
        manifest.theming.batch_size if manifest.theming else 25,
    )

    if args.dry_run:
        from src.phase2_theming.pipeline import load_normalized_reviews, preprocess_reviews

        reviews = load_normalized_reviews(paths.normalized_json)
        review_limit = manifest.theming.review_limit if manifest.theming else 1000
        truncation_words = manifest.llm.review_text_truncation if manifest.llm else 40
        preprocessed, stats = preprocess_reviews(
            reviews, review_limit=review_limit, truncation_words=truncation_words,
        )
        print(f"Dry run: {stats}")
        return

    try:
        result = run_theming(manifest, paths)
        logger.info("Phase 2 result: %s", result["status"])
        print(f"Phase 2 complete: {result['status']}")
        if result.get("analytics", {}).get("themes"):
            for tid, tinfo in result["analytics"]["themes"].items():
                print(f"  {tid}: {tinfo['review_count']} reviews, score={tinfo['theme_score']}")
    except Exception as exc:
        logger.exception("Phase 2 failed: %s", exc)
        print(f"Phase 2 FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
