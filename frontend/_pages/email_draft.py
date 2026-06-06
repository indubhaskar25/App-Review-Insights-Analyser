"""Email Draft page — preview and download the generated email draft."""

from __future__ import annotations

import json
from pathlib import Path
import streamlit as st


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


def render(data: dict, week_id: str, run_dir: Path) -> None:
    ps = data["pipeline_status"]
    email_result = data["email_result"]
    note = data["weekly_note_json"]
    publish = data["publish_result"]
    ir = data["import_report"]
    theme_config = data["theme_config"]

    # ── Top bar ───────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="top-bar">
            <div>
                <span style="color:#64748b;font-size:0.82rem;">Dashboard</span>
                <span style="color:#64748b;font-size:0.82rem;margin:0 0.4rem;">·</span>
                <span style="color:#e2e8f0;font-size:0.82rem;font-weight:600;">Email Draft</span>
            </div>
            <div class="top-bar-right">
                <span class="badge badge-ai">✦ AI Generated</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Page header + action buttons ─────────────────────────
    col_title, col_btns = st.columns([3, 2])
    with col_title:
        st.markdown(
            """
            <div class="page-header">
                <div class="page-title">Executive Summary Draft</div>
                <div class="page-subtitle">
                    Automated weekly digest prepared for stakeholders based on
                    App Store &amp; Play Store feedback.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btns:
        st.markdown("<br>", unsafe_allow_html=True)
        bc1, bc2, bc3 = st.columns(3)

        # Build email text content
        to_addr  = email_result.get("to", "—")
        subject  = email_result.get("subject", f"[Weekly Pulse] Groww — {week_id}")
        doc_url  = publish.get("doc_url", "")
        note_md  = data["weekly_note_md"]
        email_md = data["email_draft_md"]

        email_txt = f"To: {to_addr}\nSubject: {subject}\n\n{note_md}"
        if doc_url:
            email_txt += f"\n\nFull report: {doc_url}"

        with bc1:
            if st.button("📋 Copy Text", key="copy_email", use_container_width=True):
                st.toast("Email text ready — use Download below", icon="📋")
        with bc2:
            st.download_button(
                "⬇ Download .txt",
                data=email_txt.encode(),
                file_name=f"email_draft_{week_id}.txt",
                mime="text/plain",
                key="dl_email_txt",
                use_container_width=True,
            )
        with bc3:
            if email_md:
                st.download_button(
                    "⬇ Download .md",
                    data=email_md.encode(),
                    file_name=f"email_draft_{week_id}.md",
                    mime="text/markdown",
                    key="dl_email_md",
                    use_container_width=True,
                )

    # ── Draft status banner ───────────────────────────────────
    draft_id = email_result.get("draft_id", "")
    draft_status = email_result.get("status", "unknown")
    created_at = email_result.get("created_at", "")

    if draft_status == "success" and draft_id:
        st.markdown(
            f"""
            <div style="background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.25);
                        border-radius:10px;padding:0.75rem 1.25rem;margin-bottom:1.25rem;
                        display:flex;align-items:center;gap:0.75rem;">
                <span style="color:#34d399;font-size:1rem;">✓</span>
                <div>
                    <span style="font-size:0.85rem;color:#34d399;font-weight:600;">
                        Gmail Draft Created Successfully
                    </span>
                    <span style="font-size:0.78rem;color:#64748b;margin-left:1rem;">
                        Draft ID: <code style="color:#94a3b8;">{draft_id}</code>
                        &nbsp;·&nbsp; {created_at}
                    </span>
                </div>
                <div style="margin-left:auto;font-size:0.72rem;color:#64748b;">
                    ⚠ Review before sending
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);
                        border-radius:10px;padding:0.75rem 1.25rem;margin-bottom:1.25rem;">
                <span style="font-size:0.85rem;color:#fbbf24;">
                    ⚠ Gmail draft not yet created — run Phase 5 to generate
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Email preview frame ───────────────────────────────────
    # Build the whole preview as ONE HTML string so the frame actually wraps its
    # contents. Separate st.markdown calls each get their <div> auto-closed,
    # which left an empty frame with the email spilling out underneath it.
    dr = ir.get("date_range", {})
    date_range_str = f"{dr.get('start','')} – {dr.get('end','')}"
    product = note.get("product", "Groww")

    avg_rating    = data["global_avg_rating"]
    sentiment_idx = data["sentiment_index"]
    analyzed      = data["theming_report"].get("total_classifications", 0)

    browser_bar = (
        '<div class="email-browser-bar">'
        '<div class="browser-dot" style="background:#f87171;"></div>'
        '<div class="browser-dot" style="background:#fbbf24;"></div>'
        '<div class="browser-dot" style="background:#34d399;"></div>'
        f'<div class="browser-url">preview.groww.ai/draft_{week_id.replace("-","_").lower()}</div>'
        '</div>'
    )

    fields_html = (
        '<div class="email-field-row">'
        '<div class="email-field-label">To:</div>'
        f'<div class="email-field-value">{to_addr}</div>'
        '</div>'
        '<div class="email-field-row">'
        '<div class="email-field-label">Subject:</div>'
        f'<div class="email-field-value">{subject}</div>'
        '</div>'
    )

    brand_html = (
        '<div class="email-brand-header">'
        '<div>'
        f'<div class="email-brand-name">{product} <span style="color:#a78bfa;">Insights</span></div>'
        '<div class="email-brand-sub">Intelligence Layer Report</div>'
        '</div>'
        '<div style="text-align:right;">'
        f'<div style="font-size:0.78rem;color:#94a3b8;">{date_range_str}</div>'
        '<div style="font-size:0.68rem;color:#64748b;">Confidential Internal Draft</div>'
        '</div>'
        '</div>'
    )

    greeting_html = (
        '<p style="font-size:0.88rem;color:#cbd5e1;margin-bottom:0.75rem;">Hi Team,</p>'
        '<p style="font-size:0.85rem;color:#94a3b8;line-height:1.7;margin-bottom:1rem;">'
        f'Below is the automated intelligence report for <b style="color:#e2e8f0;">{product} App</b> '
        f'covering sentiment trends from {dr.get("start","")} to {dr.get("end","")}.'
        '</p>'
    )

    highlights_html = (
        '<div class="email-highlights-bar">'
        f'<div><div class="highlight-stat-value">{avg_rating}</div>'
        '<div class="highlight-stat-label">Avg Sentiment Score</div></div>'
        f'<div><div class="highlight-stat-value" style="color:#34d399;">+{sentiment_idx:.0f}%</div>'
        '<div class="highlight-stat-label">Positive Reviews</div></div>'
        f'<div><div class="highlight-stat-value">{analyzed:,}</div>'
        '<div class="highlight-stat-label">Reviews Analyzed</div></div>'
        '</div>'
    )

    theme_html = ""
    top_themes = note.get("top_themes", [])
    if top_themes:
        primary_theme = top_themes[0]
        theme_html = (
            '<h3 style="font-size:1rem;font-weight:600;color:#e2e8f0;margin:1.25rem 0 0.5rem 0;">'
            f'Key Theme: {primary_theme.get("name","")}</h3>'
            '<p style="font-size:0.85rem;color:#94a3b8;line-height:1.7;margin-bottom:1rem;">'
            f'{primary_theme.get("summary","")}</p>'
        )

    quote_html = ""
    quotes = note.get("quotes", [])
    if quotes:
        q = quotes[0]
        tid = q.get("theme_id", "")
        cfg = theme_config.get(tid, {"color": "#a78bfa"})
        qcolor = cfg["color"]
        quote_html = (
            f'<div style="border-left:3px solid {qcolor};padding:0.75rem 1rem;'
            f'background:rgba({_hex_to_rgb(qcolor)},0.06);border-radius:0 8px 8px 0;margin:1rem 0;">'
            '<div style="font-size:0.88rem;color:#cbd5e1;font-style:italic;line-height:1.6;">'
            f'"{q.get("text","")}"</div>'
            '<div style="font-size:0.72rem;color:#64748b;margin-top:0.4rem;">— Top User Review</div>'
            '</div>'
        )

    steps_section = ""
    actions = note.get("action_ideas", [])
    if actions:
        steps_html = "".join(
            f'<li style="font-size:0.85rem;color:#94a3b8;margin-bottom:0.4rem;">{a.get("text","")}</li>'
            for a in actions
        )
        steps_section = (
            '<h3 style="font-size:1rem;font-weight:600;color:#e2e8f0;margin:1.25rem 0 0.5rem 0;">Next Steps</h3>'
            f'<ul style="padding-left:1.25rem;margin:0;">{steps_html}</ul>'
        )

    doc_html = ""
    if doc_url:
        doc_html = (
            '<div style="margin-top:1.25rem;padding:0.75rem 1rem;'
            'background:rgba(167,139,250,0.08);border:1px solid rgba(167,139,250,0.2);border-radius:8px;">'
            '<span style="font-size:0.82rem;color:#94a3b8;">📄 Full report: </span>'
            f'<a href="{doc_url}" target="_blank" style="color:#a78bfa;font-size:0.82rem;text-decoration:none;">{doc_url}</a>'
            '</div>'
        )

    signature_html = (
        '<div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #2a2d3e;">'
        '<p style="font-size:0.85rem;color:#94a3b8;margin-bottom:0.25rem;">Best regards,</p>'
        f'<p style="font-size:0.88rem;font-weight:600;color:#e2e8f0;margin:0;">{product} Intelligence Pipeline</p>'
        '</div>'
        '<div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #2a2d3e;'
        'text-align:center;font-size:0.68rem;color:#64748b;">'
        'This email was automatically generated by the SaaS Insights Engine.<br>'
        '© 2024 Groww Insights · Pipeline: GitHub Actions Active'
        '</div>'
    )

    body_html = (
        '<div class="email-body-content">'
        + brand_html + greeting_html + highlights_html + theme_html
        + quote_html + steps_section + doc_html + signature_html
        + '</div>'
    )

    st.markdown(
        '<div class="email-preview-frame">' + browser_bar + fields_html + body_html + '</div>',
        unsafe_allow_html=True,
    )

    # ── Raw email draft expander ──────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 View Raw Email Draft (.md)"):
        if data["email_draft_md"]:
            st.code(data["email_draft_md"], language="markdown")
        else:
            st.info("email_draft.md not found. Run the pipeline to generate it.")

    # ── Gmail draft metadata ──────────────────────────────────
    if draft_id:
        with st.expander("📧 Gmail Draft Metadata"):
            st.json(email_result)

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
