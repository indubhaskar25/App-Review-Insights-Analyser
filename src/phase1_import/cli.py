from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.common.manifest import load_manifest
from src.common.run_paths import RunPaths, get_project_root
from src.phase1_import.pipeline import ImportPipelineError, run_import


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 1: import and normalize app reviews")
    parser.add_argument("--week-id", required=True, help="ISO week id, e.g. 2026-W20")
    parser.add_argument(
        "--manifest",
        default="config/run_manifest.yaml",
        help="Path to run manifest YAML",
    )
    args = parser.parse_args(argv)

    root = get_project_root()
    manifest_path = root / args.manifest
    manifest = load_manifest(manifest_path, root)

    if manifest.week_id != args.week_id:
        print(
            f"Warning: --week-id {args.week_id} differs from manifest week_id {manifest.week_id}",
            file=sys.stderr,
        )

    paths = RunPaths.from_manifest_run_dir(manifest.run_dir, manifest.week_id)

    try:
        report = run_import(manifest, paths)
    except ImportPipelineError as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1

    print(f"Phase 1 complete: status={report['status']}")
    print(f"  Rows written: {report['row_counts'].get('final', 0)}")
    print(f"  Output: {paths.reviews_normalized_csv}")
    print(f"  Report: {paths.import_report_json}")
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
