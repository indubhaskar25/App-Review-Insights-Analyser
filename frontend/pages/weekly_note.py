"""Weekly Note page — structured executive note with download."""

from __future__ import annotations

from pathlib import Path
import streamlit as st


def _impact_level(score: float) -> tuple[str, str]:
    """Return (label, color) for a theme score."""
    if score >= 0.45:
        return "High", "#f87171"
    if score >= 0.35:
        return "Medium", "#fbbf24"
    return "Low", "#34d399"


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


def render(data: dict, week_id: str, run_dir: Path) -> None:
    ps = data["pipeline_status"]
    note = data["weekly_note_json"]
    note_report = data["note_report"]
    ir = data["import_report"]

    # ── Top bar ───────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="top-bar">
            <div>
                <span style="color:#64748b;font-size:0.82rem;">Dashboard</span>
                <span style="color:#64748b;font-size:0.82rem;margin:0 0.4rem;">·</span>
                <span style="color:#e2e8f0;font-size:0.82rem;font-weight:600;">Weekly Note</span>
            </div>
            <div class="top-bar-right">
                <span class="badge badge-ai">✦ AI Generated</span>
                <span class="badge badge-automation">⚡ Weekly Automation</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Page header + downloads ───────────────────────────────
    dr = ir.get("date_range", {})
    start_str = dr.get("start", "")
    end_str   = dr.get("end", "")

    col_title, col_btns = st.columns([3, 2])
    with col_title:
        st.markdown(
            f"""
            <div class="page-header">
                <div class="page-title">Weekly Note: {start_str} — {end_str}</div>
                <div class="page-subtitle" style="text-transform:uppercase;letter-spacing:0.08em;font-size:0.72rem;">
                    {note.get('product','Groww')} App Performance Report
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btns:
        st.markdown("<br>", unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            md_content = data["weekly_note_md"]
            if md_content:
                st.download_button(
                    "⬇ Download Markdown",
                    data=md_content.encode(),
                    file_name=f"weekly_note_{week_id}.md",
                    mime="text/markdown",
                    key="dl_note_md",
                    use_container_width=True,
                )
        with bc2:
            # JSON download as fallback for "PDF"
            import json
            json_content = json.dumps(note, indent=2)
            st.download_button(
                "⬇ Download JSON",
                data=json_content.encode(),
                file_name=f"weekly_note_{week_id}.json",
                mime="application/json",
                key="dl_note_json",
                use_container_width=True,
            )

    # ── Executive Summary ─────────────────────────────────────
    body_md = note.get("body_markdown", "")
    # Extract prose lines (not headers, bullets, quotes)
    prose_lines = [
        ln.strip() for ln in body_md.split("\n")
        if ln.strip()
        and not ln.startswith("#")
        and not ln.startswith("*")
        and not ln.startswith(">")
        and not ln.startswith("1.")
        and not ln.startswith("2.")
        and not ln.startswith("3.")
    ]
    exec_summary = " ".join(prose_lines[:4]) if prose_lines else body_md[:400]

    # Risk status derived from avg rating
    avg_rating = data["global_avg_rating"]
    if avg_rating >= 4.0:
        risk_label, risk_color, risk_desc = "Stable", "#34d399", "Positive sentiment maintained."
    elif avg_rating >= 3.0:
        risk_label, risk_color, risk_desc = "Progressing", "#fbbf24", "Some friction areas identified."
    else:
        risk_label, risk_color, risk_desc = "At Risk", "#f87171", "High negative sentiment detected."

    word_count = note_report.get("word_count", note.get("word_count", 0))

    col_summary, col_risk = st.columns([3, 1])
    with col_summary:
        st.markdown(
            f"""
            <div class="note-section">
                <div class="note-section-title">Executive Summary</div>
                <p style="font-size:0.88rem;color:#cbd5e1;line-height:1.75;margin:0;">
                    {exec_summary}
                </p>
                <div style="margin-top:1rem;font-size:0.75rem;color:#64748b;">
                    Word count: <b style="color:#94a3b8;">{word_count}</b>/250
                    &nbsp;·&nbsp; Model: {note_report.get('call_metadata',{}).get('model','—')}
                    &nbsp;·&nbsp; Prompt: {note_report.get('prompt_version','—')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_risk:
        st.markdown(
            f"""
            <div class="note-section" style="text-align:center;height:100%;">
                <div style="font-size:0.68rem;font-weight:600;color:#64748b;
                            text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;">
                    Risk Status
                </div>
                <div style="display:inline-flex;align-items:center;gap:0.4rem;
                            padding:0.4rem 0.9rem;border-radius:20px;
                            background:rgba({_hex_to_rgb(risk_color)},0.12);
                            border:1px solid rgba({_hex_to_rgb(risk_color)},0.3);
                            margin-bottom:0.75rem;">
                    <span style="width:7px;height:7px;border-radius:50%;background:{risk_color};"></span>
                    <span style="font-size:0.82rem;font-weight:600;color:{risk_color};">{risk_label}</span>
                </div>
                <div style="font-size:0.75rem;color:#94a3b8;line-height:1.5;">{risk_desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Metric row ────────────────────────────────────────────
    total_reviews = ir.get("row_counts", {}).get("final", 0)
    sentiment_idx = data["sentiment_index"]
    analyzed      = data["theming_report"].get("total_classifications", 0)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Average Rating</div>
                <div class="metric-value">{avg_rating}</div>
                <div class="metric-sub" style="color:#fbbf24;">{"★"*int(round(avg_rating))}{"☆"*(5-int(round(avg_rating)))}</div>
            </div>
            """, unsafe_allow_html=True)
    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Review Volume</div>
                <div class="metric-value">{total_reviews:,}</div>
                <div class="metric-sub">in date window</div>
            </div>
            """, unsafe_allow_html=True)
    with m3:
        st.markdown(
            f"""
            <div class="metric-card" style="border-color:#a78bfa44;">
                <div class="metric-label">Sentiment Index</div>
                <div class="metric-value" style="color:#a78bfa;">{sentiment_idx:.0f}%</div>
                <div class="metric-sub">positive reviews</div>
            </div>
            """, unsafe_allow_html=True)
    with m4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Analyzed</div>
                <div class="metric-value">{analyzed:,}</div>
                <div class="metric-sub">reviews classified</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Top 3 Themes ──────────────────────────────────────────
    st.markdown(
        '<div class="note-section-title" style="font-size:1.1rem;font-weight:600;'
        'color:#e2e8f0;margin-bottom:1rem;">Top 3 Themes</div>',
        unsafe_allow_html=True,
    )

    top_themes = note.get("top_themes", [])
    theme_rows = {r["id"]: r for r in data["theme_rows"]}
    theme_config = data["theme_config"]

    t_cols = st.columns(3)
    for i, theme in enumerate(top_themes[:3]):
        tid = theme.get("id", "")
        row = theme_rows.get(tid, {})
        cfg = theme_config.get(tid, {"icon": "🔵", "color": "#94a3b8"})
        color = cfg["color"]
        icon  = cfg["icon"]
        score = row.get("theme_score", 0)
        impact_label, impact_color = _impact_level(score)
        review_count = row.get("review_count", 0)
        avg_r = row.get("avg_rating", 0)

        with t_cols[i]:
            st.markdown(
                f"""
                <div class="theme-detail-card">
                    <div style="width:36px;height:36px;border-radius:10px;
                                background:rgba({_hex_to_rgb(color)},0.15);
                                display:flex;align-items:center;justify-content:center;
                                font-size:1.1rem;">
                        {icon}
                    </div>
                    <div class="theme-detail-name">{theme.get('name','')}</div>
                    <div class="theme-detail-desc">{theme.get('summary','')}</div>
                    <div style="font-size:0.72rem;color:#64748b;margin-top:0.5rem;">
                        {review_count:,} reviews · {avg_r:.1f}★ avg
                    </div>
                    <div class="impact-bar-row">
                        <div style="height:3px;flex:1;background:#2a2d3e;border-radius:2px;overflow:hidden;margin-right:0.5rem;">
                            <div style="width:{min(score*200,100):.0f}%;height:100%;background:{color};border-radius:2px;"></div>
                        </div>
                        <span class="impact-level" style="color:{impact_color};">{impact_label}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── User Voices + Action Items ────────────────────────────
    col_voices, col_actions = st.columns(2, gap="medium")

    with col_voices:
        quotes = note.get("quotes", [])
        quotes_html = ""
        for q in quotes:
            tid = q.get("theme_id", "")
            cfg = theme_config.get(tid, {"color": "#94a3b8", "label": tid})
            color = cfg["color"]
            label = cfg.get("label", tid)
            quotes_html += f"""
            <div style="padding:0.85rem 0;border-bottom:1px solid #2a2d3e;">
                <div style="font-size:0.85rem;color:#cbd5e1;line-height:1.6;font-style:italic;margin-bottom:0.4rem;">
                    "{q.get('text','')}"
                </div>
                <div style="font-size:0.72rem;color:#64748b;">
                    — <span style="color:{color};">{label}</span>
                </div>
            </div>
            """

        st.markdown(
            f"""
            <div class="note-section">
                <div class="note-section-title">💬 User Voices</div>
                {quotes_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_actions:
        actions = note.get("action_ideas", [])
        action_types = ["Critical Action", "Optimization", "Feature Request", "Monitoring"]
        action_colors = ["#f87171", "#fbbf24", "#34d399", "#60a5fa"]
        actions_html = ""
        for i, action in enumerate(actions):
            atype  = action_types[i % len(action_types)]
            acolor = action_colors[i % len(action_colors)]
            tid    = action.get("theme_id", "")
            cfg    = theme_config.get(tid, {"label": tid})
            actions_html += f"""
            <div style="padding:0.85rem 0;border-bottom:1px solid #2a2d3e;">
                <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
                    <span style="width:6px;height:6px;border-radius:50%;background:{acolor};flex-shrink:0;"></span>
                    <span style="font-size:0.78rem;font-weight:600;color:{acolor};">{atype}</span>
                </div>
                <div style="font-size:0.85rem;color:#e2e8f0;font-weight:500;margin-bottom:0.2rem;">
                    {action.get('text','')}
                </div>
                <div style="font-size:0.72rem;color:#64748b;">Theme: {cfg.get('label', tid)}</div>
            </div>
            """

        st.markdown(
            f"""
            <div class="note-section">
                <div class="note-section-title">⚡ Action Items</div>
                {actions_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Raw markdown expander ─────────────────────────────────
    with st.expander("📄 View Raw Markdown"):
        st.code(data["weekly_note_md"], language="markdown")

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
