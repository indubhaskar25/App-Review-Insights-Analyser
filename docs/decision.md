# Decision Log

> **Purpose:** Record **business** and **technical** decisions for building the App Review Insights Analyser.  
> **Status key:** Accepted = locked for this build · Proposed = revisit before Phase 0 sign-off  
> **References:** [Problem Statement](./problemstatement.md) · [Architecture](./architecture.md) · [Implementation Plan](./phase-wise-implementationplan.md)

---

## How to use this file

| When | Action |
|------|--------|
| Before Phase 0 | Confirm ADR-003 MCP tools match your Cursor setup |
| Before Phase 1 | Set **BIZ-005** to your actual LIP (4) product name |
| During build | If you change a decision, add a new ADR and mark the old one **Superseded** |
| Before submission | All **Accepted** ADRs should match what you demo |

---

## Summary — decisions at a glance

| ID | Decision (short) | Status |
|----|------------------|--------|
| ADR-001 | Google Docs + Gmail via MCP only | Accepted |
| ADR-002 | Cursor agent as primary orchestrator | Accepted |
| ADR-003 | Google Workspace MCP server + tool mapping | Accepted |
| ADR-004 | Fixed legend + LLM batch classification | Accepted |
| ADR-005 | Groq Llama-3.3-70b-versatile for theming and note | Accepted |
| ADR-006 | Gmail draft only; never auto-send | Accepted |
| ADR-007 | Re-run updates same Doc per `week_id` | Accepted |
| ADR-008 | File-based artifacts under `data/runs/{week_id}/` | Accepted |
| ADR-009 | `week_id` = ISO week `YYYY-Www` | Accepted |
| ADR-010 | PII: regex redaction + pre-publish scan | Accepted |
| ADR-011 | Agent + artifacts MVP (no app codebase required) | Accepted |
| ADR-012 | Top 3 themes in note ranked by theme score | Accepted |
| ADR-013 | Quotes must be verbatim from source reviews | Accepted |
| ADR-014 | No translation in v1 | Accepted |

---

## ADR-001 — Google Workspace via MCP only

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | LIP requires W3 workflow automation with Google Docs and Gmail. Direct SDK integration duplicates OAuth handling and violates the stated MCP boundary. |
| **Decision** | All Google Docs and Gmail operations use a **configured MCP server** in Cursor. The project stores **no** Google API credentials and imports **no** Google client libraries. |
| **Consequences** | (+) Matches rubric; simpler repo; clear demo story. (−) Phases 4–5 require Cursor + MCP online; fallback is manual paste from `weekly_note.md`. |

---

## ADR-002 — Orchestration mode

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Need a fast LIP demo and a repeatable weekly process without building a custom backend. |
| **Decision** | **Primary: Cursor-native agent (Mode A).** The operator (or agent) runs each phase using the [implementation plan](./phase-wise-implementationplan.md), saves artifacts under `data/runs/{week_id}/`, and invokes MCP tools in Cursor for Phases 4–5. **Secondary:** Documented manual runbook in README for re-runs without re-explaining steps. **Out of scope for v1:** Headless scheduler, custom MCP client in application code. |
| **Consequences** | (+) Fastest path to demo video; MCP works out of the box in Cursor. (−) Weekly run is semi-manual unless you later add automation. |

---

## ADR-003 — MCP server selection

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Need one MCP server that exposes both Google Docs write and Gmail draft compose with OAuth handled server-side. |
| **Decision** | Use a **Google Workspace MCP server** (combined Docs + Gmail) registered in Cursor MCP settings. Recommended starting point: community **Google Workspace MCP** packages that document Docs + Gmail draft tools (e.g. via `npx` install per server README). After install, **copy exact tool names from Cursor’s MCP tool list** into the table below if they differ from defaults. |
| **Consequences** | Phase 4–5 agent prompts must reference **your** tool names. Update this table once in Phase 0 smoke test. |

### OAuth & scopes (via MCP server)

| Scope area | Required for |
|------------|--------------|
| Google Docs | Create/update document, write body |
| Gmail compose | Create draft only |

Do **not** request send scope unless you explicitly extend beyond LIP scope later.

### Tool mapping (default — verify in Phase 0)

| Our operation | MCP tool (use actual name from Cursor) | When |
|---------------|----------------------------------------|------|
| Create weekly Doc | `create_document` or `docs_create` | Phase 4, first run for `week_id` |
| Update Doc body | `replace_document_text` or `docs_update` | Phase 4, re-run same `week_id` |
| Get Doc URL | `get_document` or `docs_get` | Phase 4, after write |
| Create email draft | `create_draft` or `gmail_create_draft` | Phase 5 |

**Phase 0 action:** Run smoke test; replace tool names in README and here if your server uses different labels.

---

## ADR-004 — Theme grouping approach

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Hundreds of reviews must map to ≤5 themes with consistent week-over-week labels for PM trust. |
| **Decision** | **Fixed theme legend** in `config/theme_legend` (4–5 themes tied to LIP product) + **LLM batch classification** (~50 reviews per call). **Not** using embedding clustering in v1. If the LLM returns a 6th label, **merge** into the nearest canonical theme and log in `theming_report.json`. |
| **Consequences** | (+) Predictable legend in README; lower complexity. (−) Legend must be chosen well up front; major product pivots need legend update. |

### Theme score (for Phase 3 ranking)

| Factor | Weight |
|--------|--------|
| Review volume share | 40% |
| Share of ratings ≤2★ | 40% |
| Recency (reviews in last 2 weeks) | 20% |

---

## ADR-005 — LLM provider (Phases 2–3)

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Theming needs consistent JSON assignments; note generation needs reliable structure and tone within token budget. |
| **Decision** | **Groq Llama-3.3-70b-versatile** (or other Groq models like Llama 3 70B/8B) for **both** Phase 2 (classification batches) and Phase 3 (weekly note). Use **structured JSON outputs** with versioned prompts (`theme_grouping_v1`, `weekly_note_v1`). Credential: environment variable `GROQ_API_KEY` (never committed). Temperature: **0.3** for classification, **0.4** for note (slightly more natural prose). |
| **Alternatives (if blocked)** | OpenAI GPT-4o-mini, Gemini 1.5 Flash, or Claude 3.5 Haiku — update this ADR and prompt examples; keep same artifact schemas. |
| **Consequences** | High inference speed via Groq; prompts and output parsing should be verified for Llama JSON capabilities. Re-test word-count guard if switching provider. |

---

## ADR-006 — Email send policy

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Problem statement requires a draft to self/alias for human review, not automated distribution. |
| **Decision** | **Draft only** via MCP. Operator may send manually from Gmail after reviewing PII and tone. Agent must **never** invoke send or “schedule send” MCP tools. |
| **Consequences** | Lower compliance risk; no accidental mass email with store quotes. |

---

## ADR-007 — Google Doc idempotency per week

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Re-running the pipeline for the same week (fix typos, refresh quotes) should not clutter Drive with duplicate docs. |
| **Decision** | **One Doc per `week_id`.** If `publish_result.json` already contains `doc_id`, Phase 4 **updates** that document (replace body). If missing, **create** new Doc and save `doc_id` + `doc_url`. Gmail: **new draft each run** is acceptable (old drafts can be discarded manually). |
| **Consequences** | Stable Doc link for README and email footer across re-runs. |

---

## ADR-008 — Artifact storage

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Phases must hand off data without a database; evaluators need auditable outputs. |
| **Decision** | **File-based artifacts only** under `data/runs/{week_id}/`. Each phase writes CSV/JSON/MD plus a `*_report.json` with `status: success | failed`. No database, no cloud storage dependency for core pipeline. |
| **Consequences** | Easy to zip a run for submission; gitignore raw/large runs, commit redacted samples only. |

---

## ADR-009 — Week identifier format

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Weekly pulse needs a stable, sortable id for folders, Doc titles, and email subjects. |
| **Decision** | **`week_id` = ISO-8601 week:** `YYYY-Www` (e.g. `2026-W20`). Run folder: `data/runs/2026-W20/`. Date range in manifest must fall within that calendar week or span the aggregation window ending that week (document which in README). |
| **Consequences** | Aligns with “weekly” product ritual; avoid ambiguous labels like `week1`. |

---

## ADR-010 — PII handling

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Challenge forbids usernames, emails, IDs in any deliverable; store reviews often contain contact info. |
| **Decision** | **Phase 1:** Regex/heuristic redaction on title + text (emails, phones, @handles, long numeric IDs → `[REDACTED]`). **Phase 3:** Discard quote candidates that fail PII scan. **Pre-Phase 4:** Full-note scan; **block publish** if PII detected. **No** storing reviewer display names from exports. |
| **Consequences** | May occasionally redact benign numbers; prefer over-redaction to leakage. |

---

## ADR-011 — Delivery model (no custom app required)

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | LIP tests W2 prompting and W3 agent automation, not necessarily a deployed web app. |
| **Decision** | **MVP = Cursor agent + artifacts + MCP.** A separate Python/Node codebase is **optional**. Minimum submission: documented workflow, sample run folder (redacted), Google Doc link, Gmail draft proof, README re-run steps. |
| **Consequences** | Focus effort on prompt quality, theme legend, and reliable MCP publish—not UI. |

---

## ADR-012 — Which themes appear in the note

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Legend has up to 5 themes; note must highlight exactly 3. |
| **Decision** | Show **top 3 themes by theme score** (ADR-004), not simply the three largest buckets if a low-severity theme is huge. Mention remaining themes only if space allows within 250 words (usually omit). |
| **Consequences** | Note surfaces **pain + volume**, not only popularity. |

---

## ADR-013 — Quote fidelity

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Evaluators expect real user voice; hallucinated quotes undermine trust. |
| **Decision** | Every quote must include `source_review_id` traceable to `themed_reviews.json` / normalized CSV. Allow minor ellipsis (`...`) but **no** paraphrase or synthesis. Max quote length ~200 characters before ellipsis. |
| **Consequences** | Agent must reject LLM quotes that don’t match source text. |

---

## ADR-014 — Language & locale

| Field | Value |
|-------|--------|
| **Date** | 2026-05-18 |
| **Status** | Accepted |
| **Context** | Indian apps often receive Hindi/Hinglish reviews. |
| **Decision** | **No translation in v1.** Classify and quote in **original language**. Note summaries may be in **English** for leadership scanability. If a quote is non-English, keep it verbatim; optional one-line English context in theme summary only if within word budget. |
| **Consequences** | Simpler pipeline; leadership may need context for non-English quotes. |

---

## Business decisions

| ID | Date | Decision | Rationale |
|----|------|----------|-----------|
| **BIZ-001** | 2026-05-18 | Same product as **LIP challenge (4)** | Credible themes and quotes for evaluators |
| **BIZ-002** | 2026-05-18 | ≤5 themes, ≤250 words, 3+3+3 structure | Challenge constraints |
| **BIZ-003** | 2026-05-18 | **8–12 weeks** of reviews per run | Recency vs sample size |
| **BIZ-004** | 2026-05-18 | **Public CSV exports only** | No authenticated scraping |
| **BIZ-005** | 2026-05-18 | **Product name in manifest** — set to your LIP (4) app | Used in Doc title, email subject, note header |
| **BIZ-006** | 2026-05-18 | **Audience = PM / Growth / Leadership** | Executive tone, action-oriented |
| **BIZ-007** | 2026-05-18 | **Email to self or team alias** — not customers | Internal weekly pulse only |
| **BIZ-008** | 2026-05-18 | **Action ideas must be specific** — screen/flow/feature level | Avoid generic “improve UX” |

### Example theme legend (fintech / neobank — replace for your product)

| Theme id | Name | Use when reviews mention |
|----------|------|---------------------------|
| `onboarding` | Onboarding & KYC | Signup, OTP, verification, documents |
| `payments` | Payments & UPI | Transfer, bill pay, failed debit |
| `cards` | Card & ATM | Card order, ATM, limits |
| `support` | Support & comms | Chat, callback, notifications |
| `stability` | App stability | Crash, login, slow, bug |

Copy and edit into `config/theme_legend` for **your** LIP product before Phase 2.

---

## Configuration defaults (locked for build)

| Setting | Value |
|---------|--------|
| Classification batch size | 50 reviews per LLM call |
| Max themes | 5 |
| Themes in note | 3 |
| Quotes in note | 3 |
| Actions in note | 3 |
| Max note words | 250 |
| Note retry on length | Max 2 regenerations |
| Gmail | Draft only |
| Doc per week | One (update on re-run) |

---

## Out of scope (v1) — explicit non-decisions

| Item | Reason |
|------|--------|
| Auto-send email | ADR-006 |
| Direct Google APIs in repo | ADR-001 |
| Play Store / App Store API scraping | BIZ-004 |
| Real-time review streaming | Weekly batch only |
| Sentiment ML model training | LLM summarization sufficient |
| Multi-product dashboard | Single product per run |
| Slack/Teams delivery | Gmail draft only |
| Translation to English | ADR-014 |

---

## Decision review checklist (before demo)

- [ ] ADR-003 tool names match your Cursor MCP server
- [ ] BIZ-005 product name set in manifest
- [ ] Theme legend reflects **your** app (not generic example)
- [ ] OPENAI_API_KEY (or documented alternative) works for Phases 2–3
- [ ] Sample run under `data/runs/{week_id}/` with all artifacts
- [ ] Doc link + draft screenshot match ADR-006 and ADR-007

---

## Superseded decisions

| ID | Superseded by | Reason |
|----|---------------|--------|
| — | — | None yet |

---

*Newest decisions at top of ADR list when adding entries. Mark superseded ADRs with status **Superseded** and link forward.*
