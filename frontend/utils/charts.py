"""
Plotly chart builders — all return go.Figure with dark theme applied.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Shared layout defaults ────────────────────────────────────
_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#94a3b8", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor="rgba(0,0,0,0)",
        font=dict(size=11, color="#94a3b8"),
    ),
    xaxis=dict(
        gridcolor="#2a2d3e",
        linecolor="#2a2d3e",
        tickcolor="#2a2d3e",
        tickfont=dict(color="#64748b", size=10),
        showgrid=True,
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor="#2a2d3e",
        linecolor="#2a2d3e",
        tickcolor="#2a2d3e",
        tickfont=dict(color="#64748b", size=10),
        showgrid=True,
        zeroline=False,
    ),
    hoverlabel=dict(
        bgcolor="#1a1d27",
        bordercolor="#2a2d3e",
        font=dict(color="#e2e8f0", size=12),
    ),
)

THEME_COLORS = {
    "payments":    "#a78bfa",
    "onboarding":  "#34d399",
    "stability":   "#60a5fa",
    "investments": "#f472b6",
    "support":     "#fb923c",
}

SENTIMENT_COLORS = {
    "Positive": "#34d399",
    "Neutral":  "#60a5fa",
    "Negative": "#f87171",
}


def _apply_layout(fig: go.Figure, **overrides) -> go.Figure:
    layout = {**_LAYOUT, **overrides}
    fig.update_layout(**layout)
    return fig


# ── 1. Theme Distribution Donut ───────────────────────────────
def theme_donut(theme_rows: list[dict]) -> go.Figure:
    labels = [r["name"] for r in theme_rows]
    values = [r["review_count"] for r in theme_rows]
    colors = [THEME_COLORS.get(r["id"], "#94a3b8") for r in theme_rows]
    total  = sum(values)

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.65,
        marker=dict(colors=colors, line=dict(color="#0f1117", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>%{value} reviews (%{percent})<extra></extra>",
    ))

    fig.add_annotation(
        text=f"<b>{total:,}</b><br><span style='font-size:10px;color:#64748b'>Categorized</span>",
        x=0.5, y=0.5,
        font=dict(size=16, color="#e2e8f0"),
        showarrow=False,
        align="center",
    )

    _apply_layout(fig,
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#94a3b8"),
        ),
        margin=dict(l=0, r=120, t=10, b=10),
        height=260,
    )
    return fig


# ── 2. Ratings Trend Area Chart ───────────────────────────────
def ratings_trend(ratings_ts: pd.DataFrame, window: int = 30) -> go.Figure:
    if ratings_ts.empty:
        fig = go.Figure()
        _apply_layout(fig, height=220)
        return fig

    df = ratings_ts.copy()
    if window:
        cutoff = df["date"].max() - pd.Timedelta(days=window)
        df = df[df["date"] >= cutoff]

    fig = go.Figure()

    # Fill area
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["avg_rating"],
        fill="tozeroy",
        fillcolor="rgba(167,139,250,0.08)",
        line=dict(color="#a78bfa", width=2),
        mode="lines",
        name="Avg Rating",
        hovertemplate="<b>%{x|%b %d}</b><br>Avg Rating: %{y:.2f}<extra></extra>",
    ))

    _apply_layout(fig,
        height=220,
        yaxis=dict(
            range=[0, 5.5],
            gridcolor="#2a2d3e",
            tickfont=dict(color="#64748b", size=10),
            showgrid=True,
            zeroline=False,
        ),
        xaxis=dict(
            gridcolor="#2a2d3e",
            tickfont=dict(color="#64748b", size=10),
            showgrid=False,
            zeroline=False,
        ),
        showlegend=False,
    )
    return fig


# ── 3. Sentiment Distribution Grouped Bar ─────────────────────
def sentiment_by_theme(sentiment_df: pd.DataFrame, theme_config: dict) -> go.Figure:
    if sentiment_df.empty:
        fig = go.Figure()
        _apply_layout(fig, height=300)
        return fig

    fig = go.Figure()
    for sentiment, color in SENTIMENT_COLORS.items():
        sub = sentiment_df[sentiment_df["sentiment"] == sentiment]
        # Map theme_id to display name
        names = [
            theme_config.get(tid, {}).get("label", tid)
            for tid in sub["theme_id"]
        ]
        fig.add_trace(go.Bar(
            name=sentiment,
            x=names,
            y=sub["count"],
            marker_color=color,
            marker_line_width=0,
            hovertemplate=f"<b>%{{x}}</b><br>{sentiment}: %{{y}}<extra></extra>",
        ))

    _apply_layout(fig,
        barmode="group",
        height=300,
        bargap=0.25,
        bargroupgap=0.05,
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0, y=1.12,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color="#94a3b8"),
        ),
        xaxis=dict(
            gridcolor="#2a2d3e",
            tickfont=dict(color="#64748b", size=10),
            showgrid=False,
            zeroline=False,
        ),
    )
    return fig


# ── 4. Theme Score Horizontal Bar ─────────────────────────────
def theme_score_bar(theme_rows: list[dict]) -> go.Figure:
    rows = sorted(theme_rows, key=lambda x: x["theme_score"])
    names  = [r["name"] for r in rows]
    scores = [round(r["theme_score"] * 100, 1) for r in rows]
    colors = [THEME_COLORS.get(r["id"], "#94a3b8") for r in rows]

    fig = go.Figure(go.Bar(
        x=scores,
        y=names,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(width=0),
        ),
        text=[f"{s}%" for s in scores],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        hovertemplate="<b>%{y}</b><br>Impact Score: %{x}%<extra></extra>",
    ))

    _apply_layout(fig,
        height=260,
        showlegend=False,
        xaxis=dict(
            range=[0, max(scores) * 1.25 if scores else 100],
            gridcolor="#2a2d3e",
            tickfont=dict(color="#64748b", size=10),
            showgrid=True,
            zeroline=False,
            ticksuffix="%",
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(color="#e2e8f0", size=11),
            showgrid=False,
            zeroline=False,
        ),
        margin=dict(l=0, r=60, t=10, b=0),
    )
    return fig


# ── 5. Theme Sparkline (mini line per theme) ──────────────────
def theme_sparkline(theme_ts: pd.DataFrame, theme_id: str) -> go.Figure:
    if theme_ts.empty:
        fig = go.Figure()
        fig.update_layout(height=40, margin=dict(l=0, r=0, t=0, b=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    sub = theme_ts[theme_ts["theme_id"] == theme_id].sort_values("week")
    color = THEME_COLORS.get(theme_id, "#94a3b8")

    fig = go.Figure(go.Scatter(
        x=sub["week"], y=sub["count"],
        mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(color)},0.1)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=50,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


# ── 6. Rating Distribution Bar ────────────────────────────────
def rating_distribution(themed_reviews: list[dict]) -> go.Figure:
    from collections import Counter
    counts = Counter(r["rating"] for r in themed_reviews if "rating" in r)
    stars  = [1, 2, 3, 4, 5]
    values = [counts.get(s, 0) for s in stars]
    colors = ["#f87171", "#fb923c", "#fbbf24", "#a3e635", "#34d399"]

    fig = go.Figure(go.Bar(
        x=[f"{s}★" for s in stars],
        y=values,
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>%{y} reviews<extra></extra>",
    ))
    _apply_layout(fig,
        height=200,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#94a3b8", size=12)),
        yaxis=dict(gridcolor="#2a2d3e", tickfont=dict(color="#64748b", size=10)),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig


# ── Helper ────────────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
