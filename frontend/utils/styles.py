"""
Global CSS injection for the dark-theme Streamlit app.
Matches the Groww App Review Insights design system.
"""

import streamlit as st


def inject_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Google Font ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* ── Root variables ── */
        :root {
            --bg-primary:    #0f1117;
            --bg-card:       #1a1d27;
            --bg-card-hover: #1e2130;
            --bg-sidebar:    #13151f;
            --border:        #2a2d3e;
            --text-primary:  #e2e8f0;
            --text-secondary:#94a3b8;
            --text-muted:    #64748b;
            --accent-purple: #a78bfa;
            --accent-teal:   #34d399;
            --accent-blue:   #60a5fa;
            --accent-pink:   #f472b6;
            --accent-orange: #fb923c;
            --accent-red:    #f87171;
            --accent-yellow: #fbbf24;
        }

        /* ── Global reset ── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
            background-color: var(--bg-primary) !important;
            color: var(--text-primary) !important;
        }

        /* ── Hide Streamlit chrome ── */
        #MainMenu, footer, header { visibility: hidden; }
        .stDeployButton { display: none; }
        .block-container {
            padding: 1.5rem 2rem 2rem 2rem !important;
            max-width: 1400px !important;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background-color: var(--bg-sidebar) !important;
            border-right: 1px solid var(--border) !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding: 1.5rem 1rem !important;
        }

        .sidebar-brand {
            padding: 0.5rem 0.5rem 1.5rem 0.5rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 1rem;
        }
        .brand-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.3;
        }
        .brand-sub {
            font-size: 0.7rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 2px;
        }
        .sidebar-divider {
            height: 1px;
            background: var(--border);
            margin: 0.75rem 0;
        }
        .sidebar-spacer { flex: 1; min-height: 2rem; }
        .sidebar-footer {
            font-size: 0.72rem;
            color: var(--text-muted);
            text-align: center;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }
        .upgrade-btn {
            background: linear-gradient(135deg, #7c3aed, #a78bfa);
            color: white;
            text-align: center;
            padding: 0.6rem 1rem;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            margin: 0.5rem 0;
        }

        /* ── Sidebar nav buttons ── */
        [data-testid="stSidebar"] .stButton > button {
            background: transparent !important;
            border: none !important;
            color: var(--text-secondary) !important;
            text-align: left !important;
            padding: 0.55rem 0.75rem !important;
            border-radius: 8px !important;
            font-size: 0.85rem !important;
            font-weight: 400 !important;
            width: 100% !important;
            transition: all 0.15s ease !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: var(--bg-card) !important;
            color: var(--text-primary) !important;
        }

        /* ── Selectbox (week picker) ── */
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
        }

        /* ── Page header ── */
        .page-header {
            margin-bottom: 1.5rem;
        }
        .page-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }
        .page-subtitle {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }

        /* ── Metric cards ── */
        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            position: relative;
            overflow: hidden;
        }
        .metric-label {
            font-size: 0.72rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.5rem;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1;
        }
        .metric-delta-pos {
            font-size: 0.75rem;
            color: var(--accent-teal);
            font-weight: 500;
            margin-top: 0.3rem;
        }
        .metric-delta-neg {
            font-size: 0.75rem;
            color: var(--accent-red);
            font-weight: 500;
            margin-top: 0.3rem;
        }
        .metric-sub {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.3rem;
        }
        .metric-icon {
            position: absolute;
            top: 1rem;
            right: 1rem;
            font-size: 1.1rem;
            opacity: 0.5;
        }

        /* ── Content cards ── */
        .content-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }

        /* ── Bordered container = card() helper ──
           st.container(border=True) renders a wrapper that CAN hold widgets
           (charts, tables, columns), unlike a raw markdown <div>. Style it to
           match .content-card so charts/tables sit inside a real card. */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 1.25rem 1.5rem !important;
        }
        /* Keep nested bordered containers (e.g. inside columns) from doubling
           up the chrome. */
        div[data-testid="stVerticalBlockBorderWrapper"]
            div[data-testid="stVerticalBlockBorderWrapper"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
        }

        /* ── Badges ── */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.25rem 0.65rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.04em;
        }
        .badge-ai {
            background: rgba(167,139,250,0.15);
            color: var(--accent-purple);
            border: 1px solid rgba(167,139,250,0.3);
        }
        .badge-automation {
            background: rgba(52,211,153,0.12);
            color: var(--accent-teal);
            border: 1px solid rgba(52,211,153,0.25);
        }
        .badge-stable {
            background: rgba(52,211,153,0.12);
            color: var(--accent-teal);
            border: 1px solid rgba(52,211,153,0.25);
        }
        .badge-failed {
            background: rgba(248,113,113,0.12);
            color: var(--accent-red);
            border: 1px solid rgba(248,113,113,0.25);
        }
        .badge-positive {
            background: rgba(52,211,153,0.15);
            color: var(--accent-teal);
            border: 1px solid rgba(52,211,153,0.3);
        }
        .badge-negative {
            background: rgba(248,113,113,0.15);
            color: var(--accent-red);
            border: 1px solid rgba(248,113,113,0.3);
        }
        .badge-neutral {
            background: rgba(96,165,250,0.15);
            color: var(--accent-blue);
            border: 1px solid rgba(96,165,250,0.3);
        }
        .badge-week {
            background: rgba(167,139,250,0.15);
            color: var(--accent-purple);
            border: 1px solid rgba(167,139,250,0.3);
        }

        /* ── Top bar ── */
        .top-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        .top-bar-right {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .pipeline-status {
            font-size: 0.72rem;
            color: var(--text-muted);
        }
        .pipeline-dot {
            display: inline-block;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            margin-right: 4px;
        }

        /* ── Theme bar ── */
        .theme-bar-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }
        .theme-bar-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            min-width: 160px;
        }
        .theme-bar-track {
            flex: 1;
            height: 6px;
            background: var(--border);
            border-radius: 3px;
            overflow: hidden;
        }
        .theme-bar-fill {
            height: 100%;
            border-radius: 3px;
        }
        .theme-bar-pct {
            font-size: 0.78rem;
            color: var(--text-secondary);
            min-width: 36px;
            text-align: right;
        }

        /* ── Action chips ── */
        .action-chips {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }
        .action-chip {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.6rem 0.9rem;
            flex: 1;
            min-width: 140px;
        }
        .chip-type {
            font-size: 0.62rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            margin-bottom: 0.3rem;
        }
        .chip-text {
            font-size: 0.82rem;
            color: var(--text-primary);
            font-weight: 500;
        }

        /* ── Quote cards ── */
        .quote-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            transition: border-color 0.2s;
        }
        .quote-card:hover { border-color: #3a3d50; }
        .quote-text {
            font-size: 0.9rem;
            color: var(--text-primary);
            line-height: 1.6;
            font-style: italic;
            margin: 0.75rem 0;
        }
        .quote-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 0.75rem;
        }
        .quote-theme-tag {
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }
        .quote-rating {
            font-size: 0.78rem;
            color: var(--accent-yellow);
        }

        /* ── Theme table rows ── */
        .theme-table-row {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.85rem 0;
            border-bottom: 1px solid var(--border);
        }
        .theme-table-row:last-child { border-bottom: none; }
        .theme-icon-badge {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            flex-shrink: 0;
        }
        .theme-name-col { flex: 2; }
        .theme-name-text {
            font-size: 0.88rem;
            font-weight: 500;
            color: var(--text-primary);
        }
        .theme-stat-col {
            flex: 1;
            text-align: right;
            font-size: 0.82rem;
            color: var(--text-secondary);
        }

        /* ── Weekly note ── */
        .note-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.75rem;
            margin-bottom: 1rem;
        }
        .note-section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }
        .risk-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.3rem 0.75rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        /* ── Theme detail card ── */
        .theme-detail-card {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.1rem;
        }
        .theme-detail-name {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0.5rem 0 0.3rem 0;
        }
        .theme-detail-desc {
            font-size: 0.78rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }
        .impact-bar-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 0.75rem;
        }
        .impact-label {
            font-size: 0.7rem;
            color: var(--text-muted);
        }
        .impact-level {
            font-size: 0.7rem;
            font-weight: 600;
        }

        /* ── Email preview ── */
        .email-preview-frame {
            background: #1e2130;
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }
        .email-browser-bar {
            background: #252836;
            padding: 0.6rem 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 1px solid var(--border);
        }
        .browser-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .browser-url {
            background: var(--bg-card);
            border-radius: 4px;
            padding: 0.2rem 0.75rem;
            font-size: 0.72rem;
            color: var(--text-muted);
            margin-left: 0.5rem;
        }
        .email-field-row {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.6rem 1.25rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.82rem;
        }
        .email-field-label {
            color: var(--text-muted);
            min-width: 60px;
            font-weight: 500;
        }
        .email-field-value { color: var(--text-primary); }
        .email-body-content {
            padding: 1.5rem;
        }
        .email-brand-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.25rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        .email-brand-name {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        .email-brand-sub {
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .email-highlights-bar {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem 1.25rem;
            display: flex;
            gap: 2rem;
            margin: 1rem 0;
        }
        .highlight-stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        .highlight-stat-label {
            font-size: 0.68rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        /* ── Plotly chart overrides ── */
        .js-plotly-plot .plotly .modebar {
            background: transparent !important;
        }

        /* ── Streamlit overrides ── */
        .stTabs [data-baseweb="tab-list"] {
            background: transparent !important;
            gap: 0.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            color: var(--text-secondary) !important;
            font-size: 0.82rem !important;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(167,139,250,0.15) !important;
            color: var(--accent-purple) !important;
            border-color: rgba(167,139,250,0.3) !important;
        }
        .stDownloadButton > button {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
        }
        .stDownloadButton > button:hover {
            border-color: var(--accent-purple) !important;
            color: var(--accent-purple) !important;
        }
        .stButton > button {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
        }
        .stButton > button:hover {
            border-color: var(--accent-purple) !important;
        }
        div[data-testid="stMetric"] {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem 1.25rem;
        }
        div[data-testid="stMetric"] label {
            color: var(--text-muted) !important;
            font-size: 0.72rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
            font-size: 1.75rem !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            font-size: 0.75rem !important;
        }
        .stMarkdown p { color: var(--text-secondary); }
        hr { border-color: var(--border) !important; }

        /* ── Expander ── */
        .streamlit-expanderHeader {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            color: var(--text-primary) !important;
        }
        .streamlit-expanderContent {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-top: none !important;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #3a3d50; }
        </style>
        """,
        unsafe_allow_html=True,
    )
