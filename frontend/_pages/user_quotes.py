"""User Quotes page — browsable, filterable quote cards."""

from __future__ import annotations

import streamlit as st
from typing import Any


_SENTIMENT_BADGE = {
    "Positive": '<span class="badge badge-positive">Positive</span>',
    "Negative": '<span class="badge badge-negative">Negative</span>',
    "Neutral":  '<span class="badge badge-neutral">Neutral</span>',
}

_STAR_MAP = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}


def _quote_card(review: dict) -> str:
    rating   = review.get("rating", 3)
    stars    = _STAR_MAP.get(rating, "★★★☆☆")
    text     = review.get("text", "")[:300]
    theme    = review.get("theme_label", review.get("theme_id", ""))
    color    = review.get("theme_color", "#94a3b8")
    sentiment = review.get("sentiment", "Neutral")
    badge    = _SENTIMENT_BADGE.get(sentiment, "")
    store    = review.get("store", "play_store").replace("_", " ").title()
    date_str = review.get("review_date", "")

    star_color = "#34d399" if rating >= 4 else "#fbbf24" if rating == 3 else "#f87171"

    return f"""
    <div class="quote-card">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <span class="quote-theme-tag"
                  style="background:rgba({_hex_to_rgb(color)},0.15);color:{color};">
                {theme.upper()}
            </span>
            <span style="color:{star_color};font-size:0.85rem;">{stars}</span>
        </div>
        <div class="quote-text">"{text}"</div>
        <div class="quote-meta">
            <div style="font-size:0.72rem;color:#64748b;">{store} · {date_str}</div>
            {badge}
        </div>
    </div>
    """


def render(data: dict, week_id: str) -> None:
    ps = data["pipeline_status"]

    # ── Top bar ───────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="top-bar">
            <div>
                <span style="color:#64748b;font-size:0.82rem;">Dashboard</span>
                <span style="color:#64748b;font-size:0.82rem;margin:0 0.4rem;">·</span>
                <span style="color:#e2e8f0;font-size:0.82rem;font-weight:600;">Analysis</span>
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
    total_reviews = data["import_report"].get("row_counts", {}).get("final", 0)

    st.markdown(
        """
        <div class="page-header">
            <div class="page-title">User Quotes</div>
            <div class="page-subtitle">
                Visualizing individual customer sentiment through thematic lenses.
                These quotes represent the core pain points and delights identified by AI.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Filters ───────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
    with fc1:
        sentiment_filter = st.selectbox(
            "Sentiment",
            ["All Sentiments", "Positive", "Neutral", "Negative"],
            label_visibility="collapsed",
            key="uq_sentiment",
        )
    with fc2:
        theme_options = ["All Themes"] + list({r["theme_label"] for r in data["themed_reviews"]})
        theme_filter = st.selectbox(
            "Theme",
            sorted(theme_options),
            label_visibility="collapsed",
            key="uq_theme",
        )
    with fc3:
        rating_filter = st.selectbox(
            "Rating",
            ["All Ratings", "5★", "4★", "3★", "2★", "1★"],
            label_visibility="collapsed",
            key="uq_rating",
        )
    with fc4:
        sort_by = st.selectbox(
            "Sort",
            ["Newest First", "Oldest First", "Lowest Rating", "Highest Rating"],
            label_visibility="collapsed",
            key="uq_sort",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filter reviews ────────────────────────────────────────
    reviews = list(data["themed_reviews"])

    if sentiment_filter != "All Sentiments":
        reviews = [r for r in reviews if r.get("sentiment") == sentiment_filter]
    if theme_filter != "All Themes":
        reviews = [r for r in reviews if r.get("theme_label") == theme_filter]
    if rating_filter != "All Ratings":
        star_num = int(rating_filter[0])
        reviews = [r for r in reviews if r.get("rating") == star_num]

    # Sort
    if sort_by == "Newest First":
        reviews = sorted(reviews, key=lambda r: r.get("review_date", ""), reverse=True)
    elif sort_by == "Oldest First":
        reviews = sorted(reviews, key=lambda r: r.get("review_date", ""))
    elif sort_by == "Lowest Rating":
        reviews = sorted(reviews, key=lambda r: r.get("rating", 3))
    elif sort_by == "Highest Rating":
        reviews = sorted(reviews, key=lambda r: r.get("rating", 3), reverse=True)

    # ── Stats row ─────────────────────────────────────────────
    pos_count = sum(1 for r in reviews if r.get("sentiment") == "Positive")
    neg_count = sum(1 for r in reviews if r.get("sentiment") == "Negative")
    neu_count = sum(1 for r in reviews if r.get("sentiment") == "Neutral")

    st.markdown(
        f"""
        <div style="display:flex;gap:1.5rem;margin-bottom:1.25rem;flex-wrap:wrap;">
            <div style="font-size:0.8rem;color:#94a3b8;">
                Showing <b style="color:#e2e8f0;">{min(len(reviews), 30)}</b> of
                <b style="color:#e2e8f0;">{len(reviews):,}</b> reviews
            </div>
            <span class="badge badge-positive">✓ {pos_count} Positive</span>
            <span class="badge badge-neutral">~ {neu_count} Neutral</span>
            <span class="badge badge-negative">✗ {neg_count} Negative</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Representative quotes from theming_report (top section) ──
    rep_quotes = data["rep_quotes"]
    if rep_quotes and theme_filter == "All Themes" and sentiment_filter == "All Sentiments":
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:600;color:#64748b;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">'
            '✦ AI-Selected Representative Quotes</div>',
            unsafe_allow_html=True,
        )
        theme_rows = data["theme_rows"]
        rep_cols = st.columns(min(len(theme_rows), 3))
        for i, row in enumerate(theme_rows[:3]):
            tid = row["id"]
            quotes_for_theme = rep_quotes.get(tid, [])
            if not quotes_for_theme:
                continue
            q = quotes_for_theme[0]
            color = row["color"]
            with rep_cols[i % 3]:
                st.markdown(
                    f"""
                    <div class="quote-card" style="border-color:{color}33;">
                        <div style="display:flex;align-items:center;justify-content:space-between;">
                            <span class="quote-theme-tag"
                                  style="background:rgba({_hex_to_rgb(color)},0.15);color:{color};">
                                {row['name'].upper()}
                            </span>
                            <span style="color:#f87171;font-size:0.85rem;">
                                {"★" * q.get("rating",1)}{"☆" * (5-q.get("rating",1))}
                            </span>
                        </div>
                        <div class="quote-text">"{q.get('text','')[:200]}"</div>
                        <div style="font-size:0.72rem;color:#64748b;margin-top:0.5rem;">
                            Confidence: {q.get('confidence',0)*100:.0f}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

    # ── All quotes grid ───────────────────────────────────────
    PAGE_SIZE = 30
    display_reviews = reviews[:PAGE_SIZE]

    col_a, col_b = st.columns(2, gap="medium")
    for i, review in enumerate(display_reviews):
        card_html = _quote_card(review)
        if i % 2 == 0:
            with col_a:
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            with col_b:
                st.markdown(card_html, unsafe_allow_html=True)

    # ── Load more / count ─────────────────────────────────────
    st.markdown(
        f"""
        <div style="text-align:center;margin-top:1.5rem;padding:1rem;
                    border-top:1px solid #2a2d3e;">
            <div style="font-size:0.78rem;color:#64748b;">
                Viewing {min(len(reviews), PAGE_SIZE)} of {len(reviews):,} reviews
                {f'(filtered from {total_reviews:,} total)' if len(reviews) < total_reviews else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Footer ────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #2a2d3e;
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
