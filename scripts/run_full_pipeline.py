#!/usr/bin/env python3
"""Run the complete weekly review pipeline (Phases 1–5).

This script orchestrates all phases of the App Review Insights Analyzer:
  Phase 1: Import & normalize reviews from App Store + Play Store
  Phase 2: Theme classification with LLM
  Phase 3: Weekly executive note generation
  Phase 4: Publish to Google Docs via MCP
  Phase 5: Create Gmail draft via MCP

Usage:
    python scripts/run_full_pipeline.py [--manifest config/run_manifest.yaml] [--phases 1,2,3,4,5]
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# Ensure project root is on the path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.common.logging_config import setup_run_logger
from src.common.manifest import MCPConfig, load_manifest
from src.common.run_paths import RunPaths
from src.common.run_state import RunState
from src.phase1_import.pipeline import run_import_pipeline
from src.phase2_theming.pipeline import run_theming_pipeline
from src.phase3_note.pipeline import run_note_generation
from src.phase4_docs_mcp.pipeline import run_mcp_pipeline

ALL_PHASES = [1, 2, 3, 4, 5]


def run_phase_1(manifest, paths) -> None:
    print("▶ Phase 1: Import & Normalize Reviews")
    run_import_pipeline(manifest, paths)
    print("  ✓ Phase 1 complete")


def run_phase_2(manifest, paths) -> None:
    print("▶ Phase 2: Theme Classification")
    run_theming_pipeline(manifest, paths)
    print("  ✓ Phase 2 complete")


def run_phase_3(manifest, paths) -> None:
    print("▶ Phase 3: Weekly Note Generation")
    run_note_generation(manifest, paths)
    print("  ✓ Phase 3 complete")


def run_phase_4_5(manifest, paths) -> None:
    print("▶ Phase 4: Publish to Google Docs")
    from src.phase4_docs_mcp.pipeline import publish_to_google_docs
    publish_to_google_docs(manifest, paths)
    print("  ✓ Phase 4 complete")

    print("▶ Phase 5: Create Gmail Draft")
    from src.phase4_docs_mcp.pipeline import create_gmail_draft
    create_gmail_draft(manifest, paths)
    print("  ✓ Phase 5 complete")


PHASE_RUNNERS = {
    1: run_phase_1,
    2: run_phase_2,
    3: run_phase_3,
    4: run_phase_4_5,  # Runs both Phase 4 and 5
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete weekly review pipeline")
    parser.add_argument(
        "--manifest",
        default="config/run_manifest.yaml",
        help="Path to run manifest YAML (default: config/run_manifest.yaml)",
    )
    parser.add_argument(
        "--phases",
        default="1,2,3,4",
        help="Comma-separated list of phases to run (default: 1,2,3,4). "
             "Phase 4 also runs Phase 5 (Gmail draft).",
    )
    args = parser.parse_args()

    phases_to_run = [int(p.strip()) for p in args.phases.split(",")]
    manifest = load_manifest(args.manifest)
    paths = RunPaths(manifest.run_dir)
    setup_run_logger(paths)

    # Ensure run_dir exists
    paths.run_dir.mkdir(parents=True, exist_ok=True)

    # Initialize run state
    run_state_json = paths.run_state_json
    RunState.init_if_missing(run_state_json)
    state = RunState.load(run_state_json)

    print(f"\n{'='*60}")
    print(f"  Weekly Review Pipeline")
    print(f"  Product: {manifest.product}")
    print(f"  Week:    {manifest.week_id}")
    print(f"  Phases:  {phases_to_run}")
    print(f"  Run Dir: {paths.run_dir}")
    print(f"{'='*60}\n")

    # Verify Phase 1 inputs exist
    if 1 in phases_to_run:
        if not manifest.app_store_csv.exists():
            print(f"✗ ERROR: App Store CSV not found: {manifest.app_store_csv}")
            sys.exit(1)
        if not manifest.play_store_csv.exists():
            print(f"✗ ERROR: Play Store CSV not found: {manifest.play_store_csv}")
            sys.exit(1)

    failed = False
    for phase_num in sorted(phases_to_run):
        if phase_num not in PHASE_RUNNERS:
            print(f"✗ Unknown phase number: {phase_num}")
            failed = True
            continue

        phase_label = f"phase{phase_num}"
        # Skip already-completed phases
        if state.get_phase_status(phase_label) == "completed":
            print(f"⊘ Phase {phase_num} already completed, skipping")
            continue

        try:
            PHASE_RUNNERS[phase_num](manifest, paths)
        except Exception as exc:
            print(f"\n✗ Phase {phase_num} FAILED: {exc}")
            traceback.print_exc()
            failed = True
            state.mark_failed(str(run_state_json), phase_label, str(exc))
            break

    if not failed:
        print(f"\n{'='*60}")
        print("  Pipeline completed successfully!")
        print(f"{'='*60}")
        print(f"\nArtifacts in: {paths.run_dir}")
        if (paths.run_dir / "run_state.json").exists():
            state = RunState.load(paths.run_state_json)
            print(f"Run state: {state.to_dict()}")
    else:
        print(f"\n✗ Pipeline failed. Check logs at: {paths.run_log}")
        sys.exit(1)


if __name__ == "__main__":
    main()
