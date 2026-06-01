from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import os

import yaml


@dataclass
class DateRange:
    start: date
    end: date


@dataclass
class LLMConfig:
    provider: str
    model: str  # kept for backward compat; prefer model_classification / model_summary
    temperature: float
    # Dual-model fields (with defaults for backward compat)
    model_classification: str = ""
    model_summary: str = ""
    temperature_classification: float = 0.3
    temperature_summary: float = 0.4
    inter_call_delay: int = 10
    review_text_truncation: int = 40

    @property
    def effective_classification_model(self) -> str:
        """Return the classification model, falling back to `model`."""
        return self.model_classification or self.model

    @property
    def effective_summary_model(self) -> str:
        """Return the summary model, falling back to `model`."""
        return self.model_summary or self.model


@dataclass
class ThemingConfig:
    max_themes: int
    batch_size: int
    legend_path: Path
    review_limit: int = 1000


@dataclass
class MCPConfig:
    """Configuration for the Google Workspace MCP server (Phases 4–5)."""
    server_url: str = ""
    google_doc_id: str = ""

    @classmethod
    def from_env(cls) -> MCPConfig:
        """Load MCP configuration from environment variables."""
        return cls(
            server_url=os.getenv("MCP_SERVER_URL", ""),
            google_doc_id=os.getenv("GOOGLE_DOC_ID", ""),
        )


@dataclass
class RunManifest:
    product: str
    week_id: str
    date_range: DateRange
    app_store_csv: Path
    play_store_csv: Path
    run_dir: Path
    email_to: str
    email_subject_template: str
    docs_title_template: str
    llm: LLMConfig | None = None
    theming: ThemingConfig | None = None
    mcp: MCPConfig | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], project_root: Path) -> RunManifest:
        dr = data["date_range"]
        inputs = data["inputs"]
        llm_data = data["llm"]
        theming_data = data["theming"]
        return cls(
            product=data["product"],
            week_id=data["week_id"],
            date_range=DateRange(
                start=date.fromisoformat(str(dr["start"])),
                end=date.fromisoformat(str(dr["end"])),
            ),
            app_store_csv=project_root / inputs["app_store_csv"],
            play_store_csv=project_root / inputs["play_store_csv"],
            run_dir=project_root / data["outputs"]["run_dir"],
            email_to=os.getenv("EMAIL_TO", data["email"]["to"]),
            email_subject_template=data["email"]["subject_template"],
            docs_title_template=data["docs"]["title_template"],
            llm=LLMConfig(
                provider=llm_data["provider"],
                model=llm_data["model"],
                temperature=float(llm_data["temperature"]),
                model_classification=llm_data.get("model_classification", ""),
                model_summary=llm_data.get("model_summary", ""),
                temperature_classification=float(llm_data.get("temperature_classification", 0.3)),
                temperature_summary=float(llm_data.get("temperature_summary", 0.4)),
                inter_call_delay=int(llm_data.get("inter_call_delay", 10)),
                review_text_truncation=int(llm_data.get("review_text_truncation", 40)),
            ),
            theming=ThemingConfig(
                max_themes=int(theming_data["max_themes"]),
                batch_size=int(theming_data["batch_size"]),
                legend_path=project_root / theming_data["legend_path"],
                review_limit=int(theming_data.get("review_limit", 1000)),
            ),
            mcp=MCPConfig.from_env(),
        )


def load_manifest(manifest_path: Path, project_root: Path | None = None) -> RunManifest:
    root = project_root or manifest_path.resolve().parent.parent
    if manifest_path.resolve().parent.name == "config":
        root = manifest_path.resolve().parent.parent
    with manifest_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return RunManifest.from_dict(data, root)
