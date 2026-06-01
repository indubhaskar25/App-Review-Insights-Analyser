from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class RunPaths:
    week_id: str
    run_dir: Path

    @classmethod
    def from_manifest_run_dir(cls, run_dir: Path, week_id: str) -> RunPaths:
        return cls(week_id=week_id, run_dir=run_dir)

    def ensure_run_dir(self) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir

    @property
    def reviews_normalized_csv(self) -> Path:
        return self.run_dir / "reviews_normalized.csv"

    @property
    def normalized_json(self) -> Path:
        return self.run_dir / "normalized.json"

    @property
    def import_report_json(self) -> Path:
        return self.run_dir / "import_report.json"

    @property
    def run_state_json(self) -> Path:
        return self.run_dir / "run_state.json"

    @property
    def run_log(self) -> Path:
        return self.run_dir / "run.log"

    @property
    def theme_legend_json(self) -> Path:
        return self.run_dir / "theme_legend.json"

    @property
    def themed_reviews_json(self) -> Path:
        return self.run_dir / "themed_reviews.json"

    @property
    def theming_report_json(self) -> Path:
        return self.run_dir / "theming_report.json"

    # --- Phase 3 ---

    @property
    def weekly_note_json(self) -> Path:
        return self.run_dir / "weekly_note.json"

    @property
    def weekly_note_md(self) -> Path:
        return self.run_dir / "weekly_note.md"

    @property
    def note_report_json(self) -> Path:
        return self.run_dir / "note_report.json"

    # --- Phase 4 ---

    @property
    def publish_result_json(self) -> Path:
        return self.run_dir / "publish_result.json"

    @property
    def docs_report_json(self) -> Path:
        return self.run_dir / "docs_report.json"

    # --- Phase 5 ---

    @property
    def email_draft_result_json(self) -> Path:
        return self.run_dir / "email_draft_result.json"

    @property
    def gmail_report_json(self) -> Path:
        return self.run_dir / "gmail_report.json"
