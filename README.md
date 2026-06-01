# App Review Insights Analyser

Weekly pipeline: import App Store + Play Store reviews → theme → executive note → **Google Docs + Gmail via MCP**.

> **Data notice:** This project uses publicly available **Groww** App Store and Play Store reviews for **educational and portfolio purposes** only. It is **not** affiliated with Groww, and does **not** imply any official partnership or access to internal Groww data.

## Docs

- [Problem statement](docs/problemstatement.md)
- [Architecture](docs/architecture.md)
- [Implementation plan](docs/phase-wise-implementationplan.md)
- [Decisions](docs/decision.md)
- [Groww data sources](reviews_raw/GROWW_DATA_SOURCES.md)

## Setup

```bash
cd App-Review-Insights-Analyser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env with your GROQ_API_KEY, GOOGLE_DOC_ID, EMAIL_TO
```

Optional — refresh Play Store export:

```bash
pip install google-play-scraper
python scripts/fetch_groww_playstore.py
```

## Running the pipeline

### Phase 1 — Import

```bash
python -m src.phase1_import.cli --week-id 2026-W20 --manifest config/run_manifest.yaml
```

### Phase 2 — Theming

```bash
python -m src.phase2_theming --week-id 2026-W20 --manifest config/run_manifest.yaml
```

### Phase 3 — Weekly Note

```bash
python -m src.phase3_note --week-id 2026-W20 --manifest config/run_manifest.yaml
```

### Phase 4 — Google Docs (MCP)

```bash
python -m src.phase4_docs_mcp --week-id 2026-W20 --manifest config/run_manifest.yaml
```

### Phase 5 — Gmail Draft (MCP)

```bash
python -m src.phase5_gmail_mcp --week-id 2026-W20 --manifest config/run_manifest.yaml
```

> **Note:** Source `.env` before running:
> ```bash
> set -a && source .env && set +a
> ```

**Outputs** (under `data/runs/{week_id}/`):

| File | Phase |
|------|-------|
| `reviews_normalized.csv` | 1 |
| `import_report.json` | 1 |
| `theme_legend.json`, `themed_reviews.json`, `theming_report.json` | 2 |
| `weekly_note.json`, `weekly_note.md`, `note_report.json` | 3 |
| `publish_result.json`, `docs_report.json` | 4 |
| `email_draft_result.json`, `gmail_report.json` | 5 |
| `run_state.json`, `run.log` | All |

## 🤖 GitHub Actions — Automated Weekly Runs

The pipeline runs **automatically every Monday at 09:00 UTC** via GitHub Actions, with no code changes needed week to week.

### Step 1 — Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description | Required |
|--------|-------------|----------|
| `GROQ_API_KEY` | Groq LLM API key | **Yes** |
| `GOOGLE_DOC_ID` | Google Doc ID for publishing (without `/edit?...`) | For Phase 4 |
| `EMAIL_TO` | Recipient email for Gmail draft | For Phase 5 |
| `MCP_SERVER_URL` | MCP server URL — defaults to Railway deployment | Optional |

> The workflow validates `GROQ_API_KEY` at startup and fails fast with a clear message if it's missing.

### Step 2 — How to trigger manually from GitHub Actions

1. Go to your repo on GitHub.
2. Click the **Actions** tab.
3. Select **Weekly Review Pulse** from the left sidebar.
4. Click **Run workflow** (top-right dropdown button).
5. Fill in optional inputs:

   | Input | Default | Description |
   |-------|---------|-------------|
   | `week_id` | auto-detected | Override ISO week, e.g. `2026-W22`. Leave empty to use current week. |
   | `through_phase` | `5` | Stop after phase N. Use `3` to test Phases 1–3 without MCP. |
   | `skip_mcp` | `false` | Skip Phases 4–5 entirely. Useful for dry runs without Google credentials. |

6. Click **Run workflow**. The run appears in the list within seconds.

### What the workflow does

```
Checkout → Setup Python → Install deps → Validate secrets
  → Compute week_id + 12-week date window
  → Update run manifest (auto week_id + dates)
  → Fetch latest Play Store reviews (continue-on-error)
  → Phase 1: Import & Normalize
  → Phase 2: Theme Grouping          (skipped if Phase 1 failed)
  → Phase 3: Weekly Note Generation  (skipped if Phase 2 failed)
  → Phase 4: Publish to Google Docs  (skipped if Phase 3 failed or skip_mcp=true)
  → Phase 5: Create Gmail Draft      (skipped if Phase 3 failed or skip_mcp=true)
  → Generate weekly_summary.json + email_draft.md
  → Upload all artifacts (30-day retention)
  → Write GitHub Job Summary with phase table + doc link
  → On failure: auto-create GitHub Issue with remediation steps
```

Each phase is **gated** — it only runs if the previous phase succeeded.  
Each phase retries up to **3 times** (30s wait) before marking as failed.

### Artifacts produced

Every run uploads a `weekly-pulse-{week_id}` bundle (30-day retention):

| Artifact | Description |
|----------|-------------|
| `weekly_note.md` | Executive note — the main deliverable |
| `email_draft.md` | Human-readable email preview |
| `weekly_summary.json` | Consolidated run summary (phase statuses, counts, URLs) |
| `theming_report.json` | Theme stats and scores |
| `import_report.json` | Import counts and audit |
| `publish_result.json` | Google Doc URL |
| `email_draft_result.json` | Gmail draft ID |
| `run_state.json` + `run.log` | Full audit trail |

### Failure notifications

When the pipeline fails, a GitHub Issue is automatically created with:
- The failing run URL
- The week ID and trigger type
- Remediation steps (common causes + how to re-trigger)

### Zero-code weekly operation

The workflow processes a new week's reviews without any manual changes:
- `week_id` and date window are computed automatically from the current date
- Play Store reviews are refreshed automatically
- All outputs are namespaced under `data/runs/{week_id}/` — no collisions

## Theme legend (Groww)

| Theme | Covers |
|-------|--------|
| Payments & Transactions | UPI, withdrawals, charges, bank linking |
| KYC & Verification | Signup, demat, PAN/Aadhaar, documents |
| App Stability & UX | Crashes, lag, login, UI |
| Mutual Funds & Investments | SIP, MF, stocks, F&O, orders, charts |
| Support & Service | Help center, chat, callbacks, resolution |

## 🖥️ Streamlit Frontend

A production-ready dark-theme dashboard that visualises all pipeline artifacts.

### Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | default | KPI cards, executive summary, theme distribution donut, ratings trend |
| Theme Analysis | sidebar | Sentiment breakdown, impact scores, sparklines, exportable table |
| User Quotes | sidebar | Filterable quote cards with sentiment + theme tags |
| Weekly Note | sidebar | Structured note with download (MD + JSON) |
| Email Draft | sidebar | Email preview frame with download (.txt / .md) |

### Frontend setup

```bash
# Install frontend dependencies (separate from pipeline deps)
pip install -r frontend/requirements.txt

# Run the app from the project root
streamlit run frontend/app.py
```

The app opens at **http://localhost:8501**.

> The frontend reads from `data/runs/{week_id}/` — run the pipeline at least through Phase 3 first.

### Frontend structure

```
frontend/
  app.py                    # Entry point — sidebar nav + routing
  requirements.txt          # streamlit, plotly, pandas
  .streamlit/
    config.toml             # Dark theme + server config
  utils/
    data_loader.py          # Loads + enriches all JSON artifacts
    charts.py               # Plotly chart builders (donut, trend, bars, sparklines)
    styles.py               # Global CSS injection (dark theme)
  pages/
    dashboard.py            # Weekly Review Pulse overview
    theme_analysis.py       # Theme breakdown + sentiment charts
    user_quotes.py          # Filterable quote browser
    weekly_note.py          # Executive note + downloads
    email_draft.py          # Email preview + draft metadata
```

### What each page reads

| Page | Artifacts used |
|------|---------------|
| Dashboard | `import_report.json`, `theming_report.json`, `weekly_note.json`, `themed_reviews.json`, `run_state.json` |
| Theme Analysis | `theming_report.json`, `themed_reviews.json`, `import_report.json` |
| User Quotes | `themed_reviews.json`, `theming_report.json`, `import_report.json` |
| Weekly Note | `weekly_note.json`, `weekly_note.md`, `note_report.json`, `import_report.json` |
| Email Draft | `email_draft_result.json`, `email_draft.md`, `weekly_note.json`, `publish_result.json` |

### Features

- **Week selector** — switch between any run in `data/runs/`
- **Dark theme** — matches the Groww design system (Inter font, purple/teal/pink accents)
- **Plotly charts** — theme donut, ratings trend area, sentiment grouped bar, impact score bar, per-theme sparklines, rating distribution
- **Download buttons** — weekly note as `.md`, email draft as `.txt`/`.md`, theme table as `.csv`
- **Pipeline status badge** — derived from `run_state.json` (Stable / Failed / Running)
- **AI Generated badge** — shown on all pages
- **Filters** — sentiment, theme, rating, date range, sort order on User Quotes and Theme Analysis

## Tests

```bash
python -m unittest tests.test_phase1_import -v
```

## Project layout

```
.github/workflows/         # GitHub Actions CI/CD
  weekly_review_pulse.yml
frontend/                  # Streamlit dashboard (separate from pipeline)
  app.py                   # Entry point
  requirements.txt
  .streamlit/config.toml
  utils/                   # data_loader, charts, styles
  pages/                   # dashboard, theme_analysis, user_quotes, weekly_note, email_draft
src/
  common/                  # Shared utilities (manifest, PII, run state)
  phase0_foundation/       # MCP setup (manual)
  phase1_import/           # Import & normalize
  phase2_theming/          # LLM theme grouping
  phase3_note/             # LLM weekly note generation
  phase4_docs_mcp/         # Publish to Google Docs via MCP
  phase5_gmail_mcp/        # Create Gmail draft via MCP
  phase6_orchestration/    # E2E documentation
config/
  run_manifest.yaml        # Weekly run configuration
  theme_legend.yaml        # Product theme definitions
scripts/
  fetch_groww_playstore.py # Fetch latest Play Store reviews
  update_manifest.py       # Auto-update manifest (used by CI)
  run_weekly.py            # Legacy orchestrator
reviews_raw/               # groww_appstore.csv, groww_playstore.csv
data/runs/{week_id}/       # Per-week artifacts
docs/                      # Architecture, plan, decisions, phase evals
```
