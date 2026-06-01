"""
Data loader — reads all pipeline artifacts for a given run directory.
Returns a single dict consumed by all page modules.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, date
from pathlib import Path
from typing import Any

import pandas as pd


# ── Theme display config (icon + accent colour) ───────────────
THEME_CONFIG: dict[str, dict] = {
    "payments":    {"icon": "💳", "color": "#a78bfa", "label": "Payments & Transactions"},
    "onboarding":  {"icon": "🪪", "color": "#34d399", "label": "KYC & Verification"},
    "stability":   {"icon": "⚡", "color": "#60a5fa", "label": "App Stability & UX"},
    "investments": {"icon": "📈", "color": "#f472b6", "label": "Mutual Funds & Investments"},
    "support":     {"icon": "🎧", "color": "#fb923c", "label": "Support & Service"},
}

SENTIMENT_COLORS = {
    "Positive": "#34d399",
    "Neutral":  "#60a5fa",
    "Negative": "#f87171",
}


def get_available_runs(runs_dir: Path) -> list[str]:
    """Return sorted list of week_id folders, newest first."""
    if not runs_dir.exists():
        return []
    weeks = [
        d.name for d in runs_dir.iterdir()
        if d.is_dir() and re.match(r"^\d{4}-W\d{2}$", d.name)
    ]
    return sorted(weeks, reverse=True)


def _load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def _sentiment_label(rating: int | float) -> str:
    if rating >= 4:
        return "Positive"
    if rating <= 2:
        return "Negative"
    return "Neutral"


def _compute_global_avg_rating(themed_reviews: list[dict]) -> float:
    ratings = [r["rating"] for r in themed_reviews if "rating" in r]
    return round(sum(ratings) / len(ratings), 1) if ratings else 0.0


def _compute_sentiment_index(themed_reviews: list[dict]) -> float:
    """% of reviews with rating >= 4."""
    if not themed_reviews:
        return 0.0
    positive = sum(1 for r in themed_reviews if r.get("rating", 0) >= 4)
    return round(positive / len(themed_reviews) * 100, 1)


def _compute_negative_pct(themed_reviews: list[dict]) -> float:
    if not themed_reviews:
        return 0.0
    negative = sum(1 for r in themed_reviews if r.get("rating", 0) <= 2)
    return round(negative / len(themed_reviews) * 100, 1)


def _build_ratings_timeseries(themed_reviews: list[dict]) -> pd.DataFrame:
    """Daily average rating aggregated from themed_reviews."""
    rows = [
        {"date": r["review_date"], "rating": r["rating"]}
        for r in themed_reviews
        if "review_date" in r and "rating" in r
    ]
    if not rows:
        return pd.DataFrame(columns=["date", "avg_rating", "count"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    agg = (
        df.groupby("date")
        .agg(avg_rating=("rating", "mean"), count=("rating", "count"))
        .reset_index()
        .sort_values("date")
    )
    agg["avg_rating"] = agg["avg_rating"].round(2)
    return agg


def _build_theme_timeseries(themed_reviews: list[dict]) -> pd.DataFrame:
    """Weekly review count per theme for sparklines."""
    rows = [
        {"date": r["review_date"], "theme_id": r.get("theme_id", "unknown")}
        for r in themed_reviews
        if "review_date" in r
    ]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["week"] = df["date"].dt.to_period("W").apply(lambda p: p.start_time)
    agg = (
        df.groupby(["week", "theme_id"])
        .size()
        .reset_index(name="count")
    )
    return agg


def _build_sentiment_by_theme(themed_reviews: list[dict]) -> pd.DataFrame:
    """Per-theme sentiment breakdown (Positive / Neutral / Negative counts)."""
    rows = []
    for r in themed_reviews:
        rows.append({
            "theme_id": r.get("theme_id", "unknown"),
            "sentiment": _sentiment_label(r.get("rating", 3)),
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    agg = (
        df.groupby(["theme_id", "sentiment"])
        .size()
        .reset_index(name="count")
    )
    return agg


def _enrich_themed_reviews(themed_reviews: list[dict]) -> list[dict]:
    """Add sentiment label and theme display config to each review."""
    for r in themed_reviews:
        r["sentiment"] = _sentiment_label(r.get("rating", 3))
        tid = r.get("theme_id", "unknown")
        cfg = THEME_CONFIG.get(tid, {"icon": "🔵", "color": "#94a3b8", "label": tid})
        r["theme_icon"] = cfg["icon"]
        r["theme_color"] = cfg["color"]
        r["theme_label"] = cfg["label"]
    return themed_reviews


def _pipeline_status(run_state: dict | None) -> dict:
    """Derive a human-readable pipeline status summary."""
    if not run_state:
        return {"label": "Unknown", "color": "#94a3b8", "last_updated": "—"}

    phases = run_state.get("phases", {})
    all_complete = all(p.get("status") == "complete" for p in phases.values())
    any_failed = any(p.get("status") == "failed" for p in phases.values())

    label = "Stable" if all_complete else ("Failed" if any_failed else "Running")
    color = "#34d399" if all_complete else ("#f87171" if any_failed else "#fbbf24")

    # Last completed timestamp
    timestamps = [
        p.get("completed_at") for p in phases.values()
        if p.get("completed_at")
    ]
    last_updated = "—"
    if timestamps:
        latest = max(timestamps)
        try:
            dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            last_updated = dt.strftime("%b %d, %Y %H:%M UTC")
        except Exception:
            last_updated = latest

    return {"label": label, "color": color, "last_updated": last_updated}


def load_run_data(run_dir: Path) -> dict[str, Any] | None:
    """Load and enrich all artifacts for a run directory."""
    if not run_dir.exists():
        return None

    # Raw artifact loads
    import_report   = _load_json(run_dir / "import_report.json") or {}
    theming_report  = _load_json(run_dir / "theming_report.json") or {}
    weekly_note_json = _load_json(run_dir / "weekly_note.json") or {}
    note_report     = _load_json(run_dir / "note_report.json") or {}
    run_state       = _load_json(run_dir / "run_state.json") or {}
    publish_result  = _load_json(run_dir / "publish_result.json") or {}
    email_result    = _load_json(run_dir / "email_draft_result.json") or {}
    theme_legend    = _load_json(run_dir / "theme_legend.json") or {}
    weekly_summary  = _load_json(run_dir / "weekly_summary.json") or {}

    weekly_note_md  = _load_text(run_dir / "weekly_note.md") or ""
    email_draft_md  = _load_text(run_dir / "email_draft.md") or ""

    # Themed reviews (large — load carefully)
    themed_reviews_raw = _load_json(run_dir / "themed_reviews.json") or []
    themed_reviews = _enrich_themed_reviews(list(themed_reviews_raw))

    # Derived metrics
    global_avg_rating  = _compute_global_avg_rating(themed_reviews)
    sentiment_index    = _compute_sentiment_index(themed_reviews)
    negative_pct       = _compute_negative_pct(themed_reviews)
    ratings_ts         = _build_ratings_timeseries(themed_reviews)
    theme_ts           = _build_theme_timeseries(themed_reviews)
    sentiment_by_theme = _build_sentiment_by_theme(themed_reviews)
    pipeline_status    = _pipeline_status(run_state)

    # Theme analytics dict (from theming_report)
    theme_analytics = theming_report.get("analytics", {}).get("themes", {})

    # Build enriched theme rows for tables/charts
    theme_rows = []
    for tid, stats in theme_analytics.items():
        cfg = THEME_CONFIG.get(tid, {"icon": "🔵", "color": "#94a3b8", "label": tid})
        theme_rows.append({
            "id":            tid,
            "name":          stats.get("name", cfg["label"]),
            "icon":          cfg["icon"],
            "color":         cfg["color"],
            "review_count":  stats.get("review_count", 0),
            "pct_of_total":  stats.get("pct_of_total", 0.0),
            "avg_rating":    stats.get("avg_rating", 0.0),
            "low_rating_pct": stats.get("low_rating_pct", 0.0),
            "theme_score":   stats.get("theme_score", 0.0),
            "avg_confidence": stats.get("avg_confidence", 0.0),
        })
    theme_rows.sort(key=lambda x: x["theme_score"], reverse=True)

    # Representative quotes from theming_report
    rep_quotes = theming_report.get("analytics", {}).get("representative_quotes", {})

    return {
        # Raw artifacts
        "import_report":    import_report,
        "theming_report":   theming_report,
        "weekly_note_json": weekly_note_json,
        "note_report":      note_report,
        "run_state":        run_state,
        "publish_result":   publish_result,
        "email_result":     email_result,
        "theme_legend":     theme_legend,
        "weekly_summary":   weekly_summary,
        "weekly_note_md":   weekly_note_md,
        "email_draft_md":   email_draft_md,
        # Processed
        "themed_reviews":   themed_reviews,
        "theme_rows":       theme_rows,
        "rep_quotes":       rep_quotes,
        # Derived metrics
        "global_avg_rating":  global_avg_rating,
        "sentiment_index":    sentiment_index,
        "negative_pct":       negative_pct,
        "ratings_ts":         ratings_ts,
        "theme_ts":           theme_ts,
        "sentiment_by_theme": sentiment_by_theme,
        "pipeline_status":    pipeline_status,
        # Config
        "theme_config":     THEME_CONFIG,
        "sentiment_colors": SENTIMENT_COLORS,
    }
