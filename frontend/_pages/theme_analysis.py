"""Theme Analysis page — sentiment breakdown, theme table, impact scores."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from frontend.utils.charts import (
    sentiment_by_theme,
    theme_score_bar,
    theme_sparkline,
    rating_distribution,
)
from frontend.utils.layout import card


def render(data: dict, week_id: str) -> None:
    ps = data["pipeline_status"]

    # ── Top bar ───────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="top-bar">
            <div>
                <span style="color:#64748b;font-size:0.82rem;margin-right:0.5rem;">Dashboard</span>
                <span style="color:#94a3b8;font-size:0.82rem;">·</span>
                <span style="color:#e2e8f0;font-size:0.82rem;margin-left:0.5rem;font-weight:600;">Analysis</span>
            </div>
            <div class="top-bar-right">
                <span class="badge badge-ai">✦ AI Generated</span>
                <span class="badge badge-automation">⚡ Weekly Automation</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Page header ───────────────────────────────────────────
    ir = data["import_report"]
    total = ir.get("row_counts", {}).get("final", 0)

    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-title">Theme Analysis</div>
            <div class="page-subtitle">
                Uncovering critical patterns across {total:,}+ recent user reviews.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Filter bar ────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
    with fc1:
        date_filter = st.selectbox(
            "Date range",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "All Time"],
            label_visibility="collapsed",
            key="ta_date",
        )
    with fc2:
        rating_filter = st.selectbox(
            "Rating filter",
            ["All Ratings", "1★ Only", "1-2★", "3★", "4-5★"],
            label_visibility="collapsed",
            key="ta_rating",
        )
    with fc3:
        theme_filter = st.selectbox(
            "Theme filter",
            ["All Themes"] + [r["name"] for r in data["theme_rows"]],
            label_visibility="collapsed",
            key="ta_theme",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sentiment Distribution + Market Positioning ───────────
    col_sent, col_market = st.columns([3, 2], gap="medium")

    with col_sent:
        with card("Sentiment Distribution by Theme"):
            fig_sent = sentiment_by_theme(data["sentiment_by_theme"], data["theme_config"])
            st.plotly_chart(fig_sent, use_container_width=True, config={"displayModeBar": False})

    with col_market:
        sentiment_index = data["sentiment_index"]
        negative_pct    = data["negative_pct"]
        # Sentiment alpha = positive %
        sentiment_alpha = sentiment_index

        st.markdown(
            f"""
            <div class="content-card" style="text-align:center;">
                <div class="card-title" style="text-align:left;">Market Positioning</div>
                <div style="padding:1.5rem 0 1rem 0;">
                    <div style="font-size:3rem;font-weight:700;
                                background:linear-gradient(135deg,#a78bfa,#60a5fa);
                                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                        {sentiment_alpha:.0f}%
                    </div>
                    <div style="font-size:0.68rem;font-weight:600;color:#64748b;
                                text-transform:uppercase;letter-spacing:0.1em;margin-top:0.25rem;">
                        Sentiment Alpha
                    </div>
                </div>
                <div style="display:flex;justify-content:center;gap:0.5rem;margin:0.75rem 0;">
                    <div style="width:8px;height:8px;border-radius:50%;background:#a78bfa;margin-top:4px;"></div>
                    <div style="width:8px;height:8px;border-radius:50%;background:#60a5fa;margin-top:4px;"></div>
                    <div style="width:8px;height:8px;border-radius:50%;background:#34d399;margin-top:4px;"></div>
                </div>
                <div style="font-size:0.8rem;color:#94a3b8;line-height:1.5;padding:0 0.5rem;">
                    {sentiment_alpha:.0f}% positive sentiment across all themes.
                    Negative reviews account for {negative_pct:.1f}% of total.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Impact Score Chart ────────────────────────────────────
    col_impact, col_dist = st.columns(2, gap="medium")

    with col_impact:
        with card("Theme Impact Scores"):
            fig_score = theme_score_bar(data["theme_rows"])
            st.plotly_chart(fig_score, use_container_width=True, config={"displayModeBar": False})

    with col_dist:
        with card("Rating Distribution"):
            fig_dist = rating_distribution(data["themed_reviews"])
            st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Detailed Theme Breakdown Table ────────────────────────
    with card():
        col_title, col_export = st.columns([4, 1])
        with col_title:
            st.markdown('<div class="card-title">Detailed Theme Breakdown</div>', unsafe_allow_html=True)
        with col_export:
            # Build CSV for export
            rows = data["theme_rows"]
            if rows:
                df_export = pd.DataFrame([{
                    "Theme": r["name"],
                    "Reviews": r["review_count"],
                    "% of Total": f"{r['pct_of_total']:.1f}%",
                    "Avg Rating": r["avg_rating"],
                    "Low Rating %": f"{r['low_rating_pct']:.1f}%",
                    "Impact Score": f"{r['theme_score']:.3f}",
                    "Avg Confidence": f"{r['avg_confidence']:.2f}",
                } for r in rows])
                csv_bytes = df_export.to_csv(index=False).encode()
                st.download_button(
                    "⬇ Export CSV",
                    data=csv_bytes,
                    file_name=f"theme_breakdown_{week_id}.csv",
                    mime="text/csv",
                    key="export_themes",
                )

        # Table header
        st.markdown(
            """
<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1.5fr;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid #2a2d3e;margin-top:0.5rem;">
<div style="font-size:0.68rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Theme Name</div>
<div style="font-size:0.68rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Reviews</div>
<div style="font-size:0.68rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Avg Rating</div>
<div style="font-size:0.68rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">Impact Score</div>
<div style="font-size:0.68rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">30D Trend</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        # Table rows
        theme_ts = data["theme_ts"]
        for row in data["theme_rows"]:
            col_name, col_rev, col_rat, col_imp, col_spark = st.columns([2, 1, 1, 1, 1.5])

            with col_name:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.6rem;padding:0.6rem 0;">'
                    f'<div style="width:30px;height:30px;border-radius:8px;'
                    f'background:rgba({_hex_to_rgb(row["color"])},0.15);display:flex;'
                    f'align-items:center;justify-content:center;font-size:0.9rem;flex-shrink:0;">'
                    f'{row["icon"]}</div>'
                    f'<div style="font-size:0.85rem;font-weight:500;color:#e2e8f0;">{row["name"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_rev:
                st.markdown(
                    f'<div style="padding:0.6rem 0;font-size:0.85rem;color:#94a3b8;">{row["review_count"]:,}</div>',
                    unsafe_allow_html=True,
                )
            with col_rat:
                rating_color = "#34d399" if row["avg_rating"] >= 4 else "#fbbf24" if row["avg_rating"] >= 3 else "#f87171"
                st.markdown(
                    f'<div style="padding:0.6rem 0;font-size:0.85rem;color:{rating_color};">{row["avg_rating"]:.1f} ★</div>',
                    unsafe_allow_html=True,
                )
            with col_imp:
                score_pct = row["theme_score"] * 100
                bar_color = row["color"]
                st.markdown(
                    f'<div style="padding:0.6rem 0;">'
                    f'<div style="height:4px;background:#2a2d3e;border-radius:2px;overflow:hidden;margin-bottom:3px;">'
                    f'<div style="width:{min(score_pct*2,100):.0f}%;height:100%;background:{bar_color};border-radius:2px;"></div>'
                    f'</div>'
                    f'<div style="font-size:0.75rem;color:#94a3b8;">{score_pct:.1f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_spark:
                fig_spark = theme_sparkline(theme_ts, row["id"])
                st.plotly_chart(fig_spark, use_container_width=True, config={"displayModeBar": False})

            st.markdown('<div style="border-bottom:1px solid #1e2130;"></div>', unsafe_allow_html=True)

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


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
