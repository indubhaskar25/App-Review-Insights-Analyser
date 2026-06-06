"""Settings page — run info, pipeline status table, artifact health, run metadata."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


# Expected artifacts for this project
_EXPECTED_ARTIFACTS = [
    "import_report.json",
    "theming_report.json",
    "themed_reviews.json",
    "weekly_note.json",
    "weekly_note.md",
    "note_report.json",
    "email_draft_result.json",
    "email_draft.md",
    "publish_result.json",
    "docs_report.json",
    "gmail_report.json",
    "run_state.json",
    "theme_legend.json",
    "normalized.json",
    "reviews_normalized.csv",
]

_PHASE_LABELS = {
    "import":    "Phase 1 — Import",
    "theming":   "Phase 2 — Theming",
    "note_gen":  "Phase 3 — Note Generation",
    "docs_mcp":  "Phase 4 — Docs MCP",
    "gmail_mcp": "Phase 5 — Gmail MCP",
}


def _fmt_ts(ts: str | None) -> str:
    if not ts:
        return "—"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d %Y, %H:%M UTC")
    except Exception:
        return ts


def _status_badge(status: str) -> str:
    s = (status or "unknown").lower()
    if s == "complete":
        return '<span style="color:#34d399;font-weight:600;">✓ Complete</span>'
    if s in ("failed", "error"):
        return '<span style="color:#f87171;font-weight:600;">✗ Failed</span>'
    if s == "running":
        return '<span style="color:#fbbf24;font-weight:600;">⟳ Running</span>'
    return f'<span style="color:#64748b;">{status}</span>'


def _file_badge(exists: bool, size_bytes: int) -> str:
    if exists:
        if size_bytes >= 1_048_576:
            size_str = f"{size_bytes / 1_048_576:.1f} MB"
        elif size_bytes >= 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes} B"
        return f'<span style="color:#34d399;">✓ Present</span> <span style="color:#64748b;font-size:0.75rem;">({size_str})</span>'
    return '<span style="color:#f87171;">✗ Missing</span>'


def render(data: dict, week_id: str, run_dir: Path) -> None:
    ps = data["pipeline_status"]
    run_state = data.get("run_state", {})

    # ── Top bar ───────────────────────────────────────────────
    st.markdown(
        """
        <div class="top-bar">
            <div>
                <span style="color:#64748b;font-size:0.82rem;">Dashboard</span>
                <span style="color:#64748b;font-size:0.82rem;margin:0 0.4rem;">·</span>
                <span style="color:#e2e8f0;font-size:0.82rem;font-weight:600;">Settings</span>
            </div>
            <div class="top-bar-right">
                <span class="badge badge-automation">⚡ Run Diagnostics</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Page header ───────────────────────────────────────────
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-title">Settings &amp; Run Info</div>
            <div class="page-subtitle">
                Pipeline diagnostics, artifact health, and run metadata for
                <b style="color:#a78bfa;">{week_id}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Current run info card ─────────────────────────────────
    ir = data.get("import_report", {})
    dr = ir.get("date_range", {})
    total_reviews = ir.get("row_counts", {}).get("final", 0)
    analyzed = data.get("theming_report", {}).get("total_classifications", 0)
    product = run_state.get("product", ir.get("product", "Groww"))

    st.markdown(
        f"""
        <div class="content-card">
            <div class="card-title">Current Run</div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1.25rem;">
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Week ID</div>
                    <div style="font-size:1rem;font-weight:600;color:#a78bfa;">{week_id}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Product</div>
                    <div style="font-size:1rem;font-weight:600;color:#e2e8f0;">{product}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Date Range</div>
                    <div style="font-size:0.9rem;color:#e2e8f0;">{dr.get('start','—')} → {dr.get('end','—')}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Run Directory</div>
                    <div style="font-size:0.75rem;color:#94a3b8;word-break:break-all;">{run_dir}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Total Reviews</div>
                    <div style="font-size:1rem;font-weight:600;color:#e2e8f0;">{total_reviews:,}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Classified</div>
                    <div style="font-size:1rem;font-weight:600;color:#e2e8f0;">{analyzed:,}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Overall Status</div>
                    <div style="font-size:0.9rem;">{_status_badge(run_state.get('status','unknown'))}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">Last Updated</div>
                    <div style="font-size:0.82rem;color:#94a3b8;">{ps['last_updated']}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Pipeline status table ─────────────────────────────────
    col_pipeline, col_artifacts = st.columns(2, gap="medium")

    with col_pipeline:
        phases = run_state.get("phases", {})

        header_html = (
            '<div style="display:grid;grid-template-columns:2fr 1fr 1.5fr;gap:0.5rem;'
            'padding:0.4rem 0;border-bottom:1px solid #2a2d3e;margin-bottom:0.25rem;">'
            '<div style="font-size:0.65rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Phase</div>'
            '<div style="font-size:0.65rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Status</div>'
            '<div style="font-size:0.65rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Completed At</div>'
            '</div>'
        )

        rows_html = ""
        if phases:
            for phase_key, phase_data in phases.items():
                label = _PHASE_LABELS.get(phase_key, phase_key.replace("_", " ").title())
                status = phase_data.get("status", "unknown")
                completed_at = _fmt_ts(phase_data.get("completed_at"))
                rows_html += (
                    '<div style="display:grid;grid-template-columns:2fr 1fr 1.5fr;gap:0.5rem;'
                    'padding:0.6rem 0;border-bottom:1px solid #1e2130;font-size:0.82rem;">'
                    f'<div style="color:#e2e8f0;">{label}</div>'
                    f'<div>{_status_badge(status)}</div>'
                    f'<div style="color:#64748b;font-size:0.75rem;">{completed_at}</div>'
                    '</div>'
                )
        else:
            rows_html = (
                '<div style="padding:1rem 0;font-size:0.82rem;color:#64748b;">'
                'No phase data found in run_state.json</div>'
            )

        st.markdown(
            '<div class="content-card">'
            '<div class="card-title">Pipeline Phase Status</div>'
            f'{header_html}{rows_html}</div>',
            unsafe_allow_html=True,
        )

    with col_artifacts:
        header_html = (
            '<div style="display:grid;grid-template-columns:2fr 1fr;gap:0.5rem;'
            'padding:0.4rem 0;border-bottom:1px solid #2a2d3e;margin-bottom:0.25rem;">'
            '<div style="font-size:0.65rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Filename</div>'
            '<div style="font-size:0.65rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Status / Size</div>'
            '</div>'
        )

        rows_html = ""
        present_count = 0
        for filename in _EXPECTED_ARTIFACTS:
            fpath = run_dir / filename
            exists = fpath.exists()
            size = fpath.stat().st_size if exists else 0
            if exists:
                present_count += 1
            badge = _file_badge(exists, size)
            rows_html += (
                '<div style="display:grid;grid-template-columns:2fr 1fr;gap:0.5rem;'
                'padding:0.45rem 0;border-bottom:1px solid #1e2130;font-size:0.78rem;">'
                f'<div style="color:#94a3b8;font-family:monospace;font-size:0.72rem;">{filename}</div>'
                f'<div>{badge}</div>'
                '</div>'
            )

        footer_html = (
            '<div style="margin-top:0.75rem;font-size:0.75rem;color:#64748b;text-align:right;">'
            f'{present_count} / {len(_EXPECTED_ARTIFACTS)} artifacts present</div>'
        )

        st.markdown(
            '<div class="content-card">'
            '<div class="card-title">Artifact Health</div>'
            f'{header_html}{rows_html}{footer_html}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Run metadata expander ─────────────────────────────────
    with st.expander("📋 Full run_state.json"):
        st.json(run_state)

    with st.expander("📋 import_report.json"):
        st.json(data.get("import_report", {}))

    with st.expander("📋 theming_report.json (preprocessing + classification summary)"):
        # Show only top-level and preprocessing/classification, skip large batch_details
        tr = data.get("theming_report", {})
        summary = {
            k: v for k, v in tr.items()
            if k not in ("classification",)
        }
        classification = tr.get("classification", {})
        classification_summary = {
            k: v for k, v in classification.items()
            if k != "batch_details"
        }
        st.json({**summary, "classification": classification_summary})

    # ── Footer ────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #2a2d3e;
                    display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:0.72rem;color:#64748b;">© 2024 Groww Insights · Pipeline: GitHub Actions Active</div>
            <div style="font-size:0.72rem;color:#64748b;">
                <span style="color:{ps['color']};">Status: {ps['label']}</span>
                &nbsp;·&nbsp; Last Updated: {ps['last_updated']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
