#!/usr/bin/env python3
"""Run pipeline phases for a weekly review insights job."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run weekly app review pipeline")
    parser.add_argument("--week-id", required=True)
    parser.add_argument("--manifest", default="config/run_manifest.yaml")
    parser.add_argument("--through-phase", type=int, default=1, choices=range(0, 7))
    parser.add_argument("--skip-mcp", action="store_true", help="Phases 4-5 not invoked here")
    args = parser.parse_args()

    if args.through_phase >= 1:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.phase1_import.cli",
                "--week-id",
                args.week_id,
                "--manifest",
                args.manifest,
            ],
            cwd=ROOT,
        )
        if result.returncode != 0:
            return result.returncode

    if args.through_phase >= 2:
        print("Phase 2 not implemented yet — see src/phase2_theming/", file=sys.stderr)
    if args.through_phase >= 4 and not args.skip_mcp:
        print("Phases 4-5: use Cursor agent + MCP per docs/phase-wise-implementationplan.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
