"""
Groww App Review Insights Analyser — Streamlit Frontend
Entry point: streamlit run frontend/app.py

Path resolution strategy:
  - Uses __file__ to find the absolute location of this script.
  - Walks UP the directory tree until it finds a folder containing data/runs/.
  - This works regardless of cwd, Streamlit Cloud, or local invocation path.
"""

import os
import sys
from pathlib import Path

import streamlit as st


def _find_project_root() -> Path:
    """
    Walk up from __file__ until we find the directory that contains data/runs/.
    Falls back to __file__.parent.parent if not found (standard layout).
    """
    here = Path(__file__).resolve()
    # Standard layout: frontend/app.py → project root is parent.parent
    candidate = here.parent.parent
    if (candidate / "data" / "runs").exists():
        return candidate
    # Walk up further in case of unusual invocation
    for parent in here.parents:
        if (parent / "data" / "runs").exists():
            return parent
    # Final fallback
    return candidate


ROOT = _find_project_root()
RUNS_DIR = ROOT / "data" / "runs"

# Ensure project root is importable
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Change cwd so any legacy relative-path code also works
os.chdir(ROOT)

# ── Imports (after ROOT is on sys.path) ───────────────────────
from frontend.utils.data_loader import load_run_data, get_available_runs
from frontend.utils.styles import inject_css

# Import pages from _pages (underscore prevents Streamlit multi-page detection)
from frontend._pages import dashboard, theme_analysis, user_quotes, weekly_note, email_draft, settings

# ── Page config ───────────────────────────────────────────────
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

    available_runs = get_available_runs(RUNS_DIR)

    if not available_runs:
        st.error(
            f"No pipeline runs found.\n\n"
            f"**Expected location:**\n`{RUNS_DIR}`\n\n"
            f"Run the pipeline first:\n"
            f"```\npython -m src.phase1_import.cli --week-id $(date +%Y-W%V) "
            f"--manifest config/run_manifest.yaml\n```"
        )
        st.markdown(
            f"<div style='font-size:0.7rem;color:#64748b;margin-top:1rem;'>"
            f"ROOT: {ROOT}<br>RUNS_DIR exists: {RUNS_DIR.exists()}"
            f"</div>",
            unsafe_allow_html=True,
        )
        # Don't stop — allow the rest of the sidebar to render
        selected_week = None
    else:
        selected_week = st.selectbox(
            "Week",
            options=available_runs,
            index=0,
            label_visibility="collapsed",
        )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    nav_pages = {
        "📊  Dashboard":      "dashboard",
        "🎨  Theme Analysis": "theme_analysis",
        "💬  User Quotes":    "user_quotes",
        "📝  Weekly Note":    "weekly_note",
        "📧  Email Draft":    "email_draft",
        "⚙️  Settings":       "settings",
    }

    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    for label, key in nav_pages.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    st.markdown('<div class="upgrade-btn">⬆ Upgrade Plan</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-footer">Help Center &nbsp;·&nbsp; Account</div>',
        unsafe_allow_html=True,
    )

# ── No runs available — show landing page ────────────────────
if not available_runs or selected_week is None:
    st.markdown(
        f"""
        <div style="padding:3rem 2rem;text-align:center;">
            <div style="font-size:2rem;margin-bottom:1rem;">📊</div>
            <div style="font-size:1.5rem;font-weight:700;color:#e2e8f0;margin-bottom:0.5rem;">
                No Pipeline Runs Found
            </div>
            <div style="font-size:0.9rem;color:#94a3b8;max-width:480px;margin:0 auto 1.5rem auto;line-height:1.7;">
                The app is looking for run data in:<br>
                <code style="background:#1a1d27;padding:0.2rem 0.5rem;border-radius:4px;color:#a78bfa;">
                    {RUNS_DIR}
                </code>
            </div>
            <div style="font-size:0.85rem;color:#64748b;">
                Run the pipeline through at least Phase 3 to generate artifacts,
                then refresh this page.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Load data ─────────────────────────────────────────────────
run_dir = RUNS_DIR / selected_week
data = load_run_data(run_dir)

if data is None:
    st.error(
        f"Could not load run data for **{selected_week}**.\n\n"
        f"Expected artifacts in: `{run_dir}`"
    )
    st.stop()

# ── Route to active page ──────────────────────────────────────
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
elif page == "settings":
    settings.render(data, selected_week, run_dir)
