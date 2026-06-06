"""Dashboard page — Weekly Review Pulse overview."""

from __future__ import annotations

import streamlit as st
from frontend.utils.charts import theme_donut, ratings_trend
from frontend.utils.layout import card, exec_summary_text


def render(data: dict, week_id: str) -> None:
    # ── Top bar ───────────────────────────────────────────────
    ps = data["pipeline_status"]
    dot_color = ps["color"]

    st.markdown(
        f"""
        <div class="top-bar">
            <div>
                <span style="color:#94a3b8;font-size:0.82rem;margin-right:0.5rem;">Dashboard</span>
                <span style="color:#64748b;font-size:0.82rem;">·</span>
                <span style="color:#64748b;font-size:0.82rem;margin-left:0.5rem;">Analysis</span>
            </div>
            <div class="top-bar-right">
                <span class="badge badge-ai">✦ AI Generated</span>
                <span class="badge badge-automation">⚡ Weekly Automation</span>
                <span class="pipeline-status">
                    <span class="pipeline-dot" style="background:{dot_color};"></span>
                    Pipeline: <b style="color:{dot_color};">{ps['label']}</b>
                    &nbsp;·&nbsp; {ps['last_updated']}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Page header ───────────────────────────────────────────
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-title">Weekly Review Pulse</div>
            <div class="page-subtitle">
                Real-time sentiment and performance tracking across play stores.
                &nbsp;·&nbsp; <b style="color:#a78bfa;">{week_id}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Metric cards ──────────────────────────────────────────
    ir = data["import_report"]
    tr = data["theming_report"]
    total_reviews   = ir.get("row_counts", {}).get("final", 0)
    avg_rating      = data["global_avg_rating"]
    negative_pct    = data["negative_pct"]
    analyzed        = tr.get("total_classifications", 0)
    review_limit    = tr.get("preprocessing", {}).get("review_limit", 1000)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">💬</div>
                <div class="metric-label">Total Reviews</div>
                <div class="metric-value">{total_reviews:,}</div>
                <div class="metric-sub">in date window</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        stars = "★" * int(round(avg_rating)) + "☆" * (5 - int(round(avg_rating)))
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">📈</div>
                <div class="metric-label">Average Rating</div>
                <div class="metric-value">{avg_rating}</div>
                <div class="metric-sub" style="color:#fbbf24;">{stars}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        neg_color = "#f87171" if negative_pct > 15 else "#fbbf24" if negative_pct > 8 else "#34d399"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">😟</div>
                <div class="metric-label">Negative Review %</div>
                <div class="metric-value" style="color:{neg_color};">{negative_pct}%</div>
                <div class="metric-sub">ratings ≤ 2★</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-icon">⚡</div>
                <div class="metric-label">Analyzed This Week</div>
                <div class="metric-value">{analyzed:,}</div>
                <div class="metric-sub">/ {review_limit:,} cap</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Executive Summary + Top 3 Themes ─────────────────────
    col_left, col_right = st.columns([3, 2], gap="medium")

    with col_left:
        note = data["weekly_note_json"]
        action_ideas = note.get("action_ideas", [])

        # Build a clean summary from structured note data (body_markdown is all
        # headers/bullets, so naive prose extraction would leak raw markdown).
        summary_text = exec_summary_text(note)

        # Chip types by position
        chip_types = ["CRITICAL ACTION", "WINNING FEATURE", "TREND ALERT"]
        chip_colors = ["#f87171", "#34d399", "#fbbf24"]

        chips_html = ""
        for i, action in enumerate(action_ideas[:3]):
            ctype = chip_types[i] if i < len(chip_types) else "ACTION"
            ccolor = chip_colors[i] if i < len(chip_colors) else "#94a3b8"
            chips_html += f"""
            <div class="action-chip">
                <div class="chip-type" style="color:{ccolor};">{ctype}</div>
                <div class="chip-text">{action.get('text','')}</div>
            </div>
            """

        st.markdown(
            f"""
            <div class="content-card">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
                    <div class="card-title" style="margin-bottom:0;">Executive Summary</div>
                    <span class="badge badge-week">Week {week_id.split('-W')[-1]} AI Report</span>
                </div>
                <p style="font-size:0.88rem;color:#cbd5e1;line-height:1.7;margin-bottom:1rem;">
                    {summary_text}
                </p>
                <div class="action-chips">{chips_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        theme_rows = data["theme_rows"]
        top3 = theme_rows[:3]

        # Build the whole card as one flat HTML string. Mixing injected HTML
        # with indented trailing markup makes Streamlit's markdown parser treat
        # the trailing block as an indented code block, so keep it unindented.
        bars_html = ""
        for row in top3:
            pct = row["pct_of_total"]
            color = row["color"]
            bars_html += (
                '<div class="theme-bar-row">'
                f'<div class="theme-bar-label">{row["icon"]} {row["name"]}</div>'
                '<div class="theme-bar-track">'
                f'<div class="theme-bar-fill" style="width:{min(pct*2.5,100):.0f}%;background:{color};"></div>'
                '</div>'
                f'<div class="theme-bar-pct">{pct:.0f}%</div>'
                '</div>'
            )

        footer_html = (
            '<div style="margin-top:1rem;font-size:0.75rem;color:#64748b;text-align:right;">'
            f'{len(theme_rows)} themes total</div>'
        )

        st.markdown(
            '<div class="content-card" style="height:100%;">'
            '<div class="card-title">Top 3 Themes</div>'
            f'{bars_html}{footer_html}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Theme Distribution + Ratings Trend ────────────────────
    col_chart1, col_chart2 = st.columns(2, gap="medium")

    with col_chart1:
        with card("Theme Distribution"):
            fig_donut = theme_donut(data["theme_rows"])
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

    with col_chart2:
        with card():
            col_title, col_toggle = st.columns([3, 1])
            with col_title:
                st.markdown('<div class="card-title">Ratings Trend</div>', unsafe_allow_html=True)
            with col_toggle:
                window = st.selectbox(
                    "window",
                    options=[7, 30, 90],
                    index=1,
                    format_func=lambda x: f"{x}D",
                    label_visibility="collapsed",
                    key="ratings_window",
                )
            fig_trend = ratings_trend(data["ratings_ts"], window=window)
            st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    # ── Footer ────────────────────────────────────────────────
    dr = ir.get("date_range", {})
    st.markdown(
        f"""
        <div style="margin-top:2rem;padding-top:1rem;border-top:1px solid #2a2d3e;
                    display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:0.72rem;color:#64748b;">
                © 2024 Groww Insights · Pipeline: GitHub Actions Active
            </div>
            <div style="font-size:0.72rem;color:#64748b;">
                Data window: {dr.get('start','—')} → {dr.get('end','—')}
                &nbsp;·&nbsp;
                <span style="color:{dot_color};">Status: {ps['label']}</span>
                &nbsp;·&nbsp; Last Updated: {ps['last_updated']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
