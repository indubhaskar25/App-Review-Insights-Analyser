"""Phase 3 – Weekly Note Generation CLI

Usage:
    python -m src.phase3_note --manifest config/run_manifest.yaml
    python -m src.phase3_note --week-id 2026-W20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.common.logging_config import setup_run_logger
from src.common.manifest import load_manifest
from src.common.run_paths import RunPaths, get_project_root
from src.phase3_note.pipeline import run_note_generation


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Phase 3: Weekly Note Generation")
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
    args = parser.parse_args(argv)

    root = get_project_root()
    manifest_path = args.manifest or root / "config" / "run_manifest.yaml"
    manifest = load_manifest(manifest_path, root)

    if args.week_id:
        manifest.week_id = args.week_id
        manifest.run_dir = root / "data" / "runs" / args.week_id

    paths = RunPaths.from_manifest_run_dir(manifest.run_dir, manifest.week_id)

    # Setup logger
    logger = setup_run_logger(paths.run_log, "phase3")

    logger.info(
        "Phase 3 starting: product=%s week_id=%s model=%s",
        manifest.product,
        manifest.week_id,
        manifest.llm.effective_summary_model if manifest.llm else "N/A",
    )

    try:
        result = run_note_generation(manifest, paths)
        logger.info("Phase 3 result: %s", result["status"])
        print(f"Phase 3 complete: {result['status']}")
        print(f"  Word count: {result.get('word_count', 0)}")
        print(f"  Retries: {result.get('retries', 0)}")
        if result.get("top_themes"):
            for t in result["top_themes"]:
                print(f"  Theme: {t['name']} (score={t['theme_score']})")
    except Exception as exc:
        logger.exception("Phase 3 failed: %s", exc)
        print(f"Phase 3 FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
