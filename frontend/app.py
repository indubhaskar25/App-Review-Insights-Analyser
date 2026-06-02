"""
Groww App Review Insights Analyser — Streamlit Frontend
Entry point: streamlit run frontend/app.py
"""

import streamlit as st
from pathlib import Path
import sys

# Ensure project root is importable regardless of working directory
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Also change cwd to project root so relative paths work
import os
os.chdir(ROOT)

from frontend.utils.data_loader import load_run_data, get_available_runs
from frontend.utils.styles import inject_css
from frontend._pages import dashboard, theme_analysis, user_quotes, weekly_note, email_draft

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Groww App Review Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-title">Groww App Review</div>
            <div class="brand-sub">SaaS Insights</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Week selector
    available_runs = get_available_runs(ROOT / "data" / "runs")
    if not available_runs:
        st.error("No pipeline runs found in data/runs/")
        st.stop()

    selected_week = st.selectbox(
        "Week",
        options=available_runs,
        index=0,
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # Navigation
    pages = {
        "📊  Dashboard": "dashboard",
        "🎨  Theme Analysis": "theme_analysis",
        "💬  User Quotes": "user_quotes",
        "📝  Weekly Note": "weekly_note",
        "📧  Email Draft": "email_draft",
    }

    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    for label, key in pages.items():
        active = "nav-active" if st.session_state.page == key else ""
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)

    # Upgrade CTA
    st.markdown(
        '<div class="upgrade-btn">⬆ Upgrade Plan</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-footer">Help Center &nbsp;·&nbsp; Account</div>', unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────
run_dir = ROOT / "data" / "runs" / selected_week
data = load_run_data(run_dir)

if data is None:
    st.error(f"Could not load run data for {selected_week}. Run the pipeline first.")
    st.stop()

# ── Route to page ─────────────────────────────────────────────
page = st.session_state.page

if page == "dashboard":
    dashboard.render(data, selected_week)
elif page == "theme_analysis":
    theme_analysis.render(data, selected_week)
elif page == "user_quotes":
    user_quotes.render(data, selected_week)
elif page == "weekly_note":
    weekly_note.render(data, selected_week, run_dir)
elif page == "email_draft":
    email_draft.render(data, selected_week, run_dir)
