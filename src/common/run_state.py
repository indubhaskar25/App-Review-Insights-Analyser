from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_run_state(path: Path) -> dict[str, Any]:
    if path.exists():
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    return {
        "week_id": "",
        "current_phase": "created",
        "status": "in_progress",
        "phases": {},
    }


def save_run_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def update_phase_status(
    path: Path,
    week_id: str,
    phase_key: str,
    status: str,
    *,
    current_phase: str | None = None,
) -> dict[str, Any]:
    state = load_run_state(path)
    state["week_id"] = week_id
    if current_phase:
        state["current_phase"] = current_phase
    phases = state.setdefault("phases", {})
    entry = phases.setdefault(phase_key, {})
    entry["status"] = status
    if status == "complete":
        entry["completed_at"] = _utc_now()
    elif status == "in_progress":
        entry["started_at"] = _utc_now()
    if status == "failed":
        state["status"] = "failed"
    elif all(
        phases.get(k, {}).get("status") == "complete"
        for k in ("import", "theming", "note_gen", "docs_mcp", "gmail_mcp")
        if k in phases
    ):
        state["status"] = "complete"
    save_run_state(path, state)
    return state


class RunState:
    """Thin wrapper for run state file operations."""

    def __init__(self, path: Path, week_id: str) -> None:
        self.path = path
        self.week_id = week_id

    def mark_phase(self, phase_key: str, status: str, current_phase: str | None = None) -> None:
        update_phase_status(self.path, self.week_id, phase_key, status, current_phase=current_phase)
