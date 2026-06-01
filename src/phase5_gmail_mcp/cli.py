"""CLI entry point for Phase 5: Gmail draft."""

from __future__ import annotations

import argparse

from src.common.logging_config import setup_run_logger
from src.common.manifest import load_manifest
from src.common.run_paths import RunPaths
from src.phase4_docs_mcp.pipeline import create_gmail_draft


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5: Create Gmail draft with weekly note via MCP")
    parser.add_argument("--manifest", default="config/run_manifest.yaml", help="Path to run manifest YAML")
    parser.add_argument("--week-id", default=None, help="Override week_id from manifest (e.g. 2026-W20)")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    if args.week_id:
        manifest.week_id = args.week_id

    paths = RunPaths(manifest.run_dir)
    setup_run_logger(paths)

    create_gmail_draft(manifest, paths)


if __name__ == "__main__":
    main()
