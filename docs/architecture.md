# Architecture — App Review Insights Analyser

> **Reference:** [Problem Statement](./problemstatement.md) · [Phase-Wise Implementation Plan](./phase-wise-implementationplan.md) · [Decisions](./decision.md)  
> **Style:** Agent-orchestrated pipeline with **MCP** for Google Workspace; local workflow for ingest, theming, and LLM note generation.

---

## Table of contents

1. [System overview](#1-system-overview)
2. [Architectural principles](#2-architectural-principles)
3. [Runtime model](#3-runtime-model)
4. [Component layers](#4-component-layers)
5. [Phase-by-phase architecture](#5-phase-by-phase-architecture)
6. [Data contracts & artifacts](#6-data-contracts--artifacts)
7. [MCP integration architecture](#7-mcp-integration-architecture)
8. [Agent & orchestration design](#8-agent--orchestration-design)
9. [Configuration](#9-configuration)
10. [Folder structure (logical)](#10-folder-structure-logical)
11. [Cross-cutting concerns](#11-cross-cutting-concerns)
12. [Security & compliance](#12-security--compliance)
13. [Observability & debugging](#13-observability--debugging)
14. [Phase dependencies](#14-phase-dependencies)
15. [Non-functional requirements](#15-non-functional-requirements)
16. [Failure domains & edge cases](#16-failure-domains--edge-cases)

---

## 1. System overview

### 1.1 What we are building

A **weekly review insights agent** that:

1. Accepts **public** App Store and Play Store CSV exports (8–12 weeks).
2. Normalizes and redacts reviews locally.
3. Groups reviews into **≤5 product themes** using an LLM (optional embedding assist).
4. Generates a **≤250-word** executive note (3 themes, 3 quotes, 3 actions).
5. Publishes the note to **Google Docs** via **MCP tools only**.
6. Creates a **Gmail draft** via **MCP tools only** (never auto-sends).

The **orchestrator** is a Cursor AI agent (recommended) or a documented weekly runbook. Phases 1–3 are **local agent + LLM** work with saved artifacts. Phases 4–5 are **MCP tool calls only**—no direct Google APIs in the project.

### 1.2 High-level diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATION LAYER                                         │
│  Run manifest · Run state · Phase gates · Cursor agent (MCP for Docs + Gmail)            │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
    ┌────────────┬────────────┬───────────────┼───────────────┬────────────┬────────────┐
    ▼            ▼            ▼               ▼               ▼            ▼            ▼
┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐
│Phase 0 │ │ Phase 1  │ │ Phase 2  │ │   Phase 3    │ │ Phase 4  │ │Phase 5  │ │Phase 6  │
│MCP +   │ │ Import   │ │ Theming  │ │ Note (LLM)   │ │Docs MCP  │ │Gmail MCP│ │E2E      │
│setup   │ │ + PII    │ │ (LLM)    │ │              │ │          │ │         │ │         │
└────────┘ └──────────┘ └──────────┘ └──────────────┘ └────┬─────┘ └────┬────┘ └─────────┘
                                                              │            │
                                                              └─────┬──────┘
                                                                    ▼
                                                    ┌───────────────────────────────┐
                                                    │ Google Workspace MCP Server   │
                                                    │ OAuth · token refresh · scopes│
                                                    └───────────────────────────────┘
```

### 1.3 Design goals

| Goal | How architecture supports it |
|------|------------------------------|
| **Reproducible weekly runs** | Immutable `data/runs/{week_id}/` artifact folders |
| **Evaluator-friendly demo** | JSON reports + Doc link + draft screenshot per run |
| **MCP compliance** | Hard boundary: Google Docs/Gmail only via MCP tools |
| **Agent composability** | Small structured artifacts between phases; versioned prompts |
| **Safe outputs** | PII redaction at import + pre-publish scan |

---

## 2. Architectural principles

| Principle | Implication | Violation example |
|-----------|-------------|-------------------|
| **Phase isolation** | Phase N only reads Phase N−1 outputs + manifest | Note generation reading raw CSV directly |
| **MCP boundary** | Docs/Gmail = MCP tools only | Embedding Google API credentials in the repo |
| **Artifact-first** | Every phase writes machine-readable outputs | Only chat output, nothing saved |
| **Fail loud** | Phase reports show `failed` with a clear reason | Empty theme list with no error |
| **Idempotent weeks** | Same `week_id` → update existing Doc, not duplicates | Multiple Docs for one week |
| **Prompt versioning** | Prompts named by version; referenced in reports | One-off prompts not tracked |
| **No PII leakage** | Redact early; scan before MCP publish | Publishing reviewer handles |

---

## 3. Runtime model

### 3.1 Execution modes

| Mode | Who runs phases | Phases 1–3 | Phases 4–5 | Best for |
|------|-----------------|------------|------------|----------|
| **A — Cursor agent** | You + Cursor Agent | Agent follows runbook; saves artifacts | Agent invokes MCP in IDE | LIP demo, fastest MVP |
| **B — Documented manual** | You step through plan | Same, guided by implementation plan | MCP steps in Cursor | Learning / low automation |
| **C — Hybrid** | Automated prep + agent publish | Exports + manifests prepared | Agent only for MCP | Balanced |

Record chosen mode in [decision.md](./decision.md) ADR-002.

### 3.2 Run lifecycle

| State | Phase | Meaning |
|-------|-------|---------|
| Created | — | `week_id` folder and manifest ready |
| Importing | 1 | CSVs being normalized |
| Theming | 2 | Reviews being classified |
| Note generation | 3 | Weekly pulse being written |
| Docs (MCP) | 4 | Publishing to Google Docs |
| Gmail (MCP) | 5 | Draft being created |
| Complete | 6 | All deliverables ready |
| Failed | Any | Stop; fix before continuing |

Track progress in `data/runs/{week_id}/run_state.json` with per-phase status and timestamps.

### 3.3 Phase gate protocol

Before starting Phase N+1:

1. Confirm Phase N report shows **success**.
2. Confirm required artifacts exist (see [§6](#6-data-contracts--artifacts)).
3. Complete the phase [eval.md](./phases/) checklist.
4. Log any exceptions in [decision.md](./decision.md).

---

## 4. Component layers

### 4.1 Layer diagram

```
┌─────────────────────────────────────────────────────────────┐
│ L4  Presentation / Deliverables  (README, demo, screenshots)│
├─────────────────────────────────────────────────────────────┤
│ L3  Integration (MCP)              Google Docs + Gmail draft│
├─────────────────────────────────────────────────────────────┤
│ L2  Intelligence (LLM)             Theming + note synthesis │
├─────────────────────────────────────────────────────────────┤
│ L1  Data processing                Import, merge, PII, filter│
├─────────────────────────────────────────────────────────────┤
│ L0  Infrastructure                 Config, logging, run state│
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Shared capabilities (all phases)

| Capability | Responsibility |
|------------|----------------|
| **Run manifest** | Single config: product, dates, CSV paths, email recipient, doc title |
| **Run paths** | Standard folder per `week_id` under `data/runs/` |
| **Run state** | Which phases completed; timestamps |
| **PII handling** | Redact on import; scan before publish |
| **LLM access** | Theming + note generation with structured outputs |
| **Validation** | Enforce theme cap, word limit, required fields |
| **Logging** | Per-run log for debugging and demo evidence |

### 4.3 Orchestration

| Component | Responsibility |
|-----------|----------------|
| **Weekly runbook** | Ordered steps for operator or agent |
| **Phase gates** | eval.md checklists before advancing |
| **Agent system prompt** | Rules: MCP-only for Google, constraints, fail-stop |

---

## 5. Phase-by-phase architecture

### Phase 0 — Foundation & MCP setup

**Goal:** Prove MCP works; establish config templates and decisions before data work.

| Activity | Outcome |
|----------|---------|
| Select Google Workspace MCP server | ADR-003 tool mapping filled |
| Configure MCP in Cursor | Server connects; OAuth complete |
| Smoke test | Test Doc created; test Gmail draft created (not sent) |
| Templates | `run_manifest`, theme legend starter, folder layout |

### Phase 1 — Import & normalization

**Goal:** One canonical review dataset for the date window, PII-redacted.

```
App Store CSV ──▶ Adapter ──┐
                          ├──▶ Merge ──▶ Date filter ──▶ PII redact ──▶ Normalized CSV
Play Store CSV ─▶ Adapter ─┘
```

| Step | Description |
|------|-------------|
| Parse exports | Map store-specific columns to canonical fields |
| Merge | Combine both stores |
| Dedupe | One row per review (native id or content hash) |
| Filter | Keep only 8–12 week window from manifest |
| Redact | Remove emails, phones, handles, long IDs |
| Report | Counts: raw, merged, filtered, redactions, drops |

**Canonical review fields:** `review_id`, `store`, `rating`, `title`, `text`, `review_date`

**Typical column mapping:**

| Canonical | App Store (typical) | Play Store (typical) |
|-----------|---------------------|----------------------|
| Date | Created | Review Submit Date |
| Rating | Rating | Star Rating |
| Text | Review / Body | Review Text |
| Title | Title | — |

---

### Phase 2 — Theme grouping

**Goal:** Every review assigned to **one** of **≤5** themes; legend + analytics for Phase 3.

#### 2a. Model strategy (Groq rate-limit aware)

Groq free-tier limits for `llama-3.3-70b-versatile` are tight (30 RPM, 1K RPD, 12K TPM, 100K TPD). Processing 1,000 reviews through the 70B model for classification would consume nearly the entire daily token budget, leaving no room for Phase 3 or retries. We support two configurations:

**Recommended: Dual-model**

| Role | Model | Why |
|------|-------|-----|
| **Bulk classification** (Phase 2) | `llama-3.1-8b-instant` | 30 RPM, **14.4K RPD**, 6K TPM, **500K TPD** — 5× daily token budget vs 70B. Excellent accuracy for structured JSON classification. |
| **Executive summary** (Phase 3) | `llama-3.3-70b-versatile` | Superior reasoning, tone control, synthesis. Only **1–2 calls** needed. |

This mirrors production AI systems where lightweight models handle high-volume structured tasks and heavyweight models are reserved for low-volume creative synthesis.

**Fallback: Single-model (70B only)**

If `llama-3.1-8b-instant` is unavailable, Phase 2 can run on `llama-3.3-70b-versatile` alone with strict constraints:

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Review text truncation | First 40 words (~50 tokens) | Classification needs topic signal, not full text |
| Batch size | 25 reviews | Keeps each call under 2,000 tokens |
| Inter-call delay | 10 seconds | Stays under 12K TPM (~6 calls/min) |
| Review limit | 1,000 (no increase) | 40 batches × ~2,000 tokens = ~80K TPD, leaves ~20K for Phase 3 |
| Phase 3 same-day | Yes — combined budget ~90K of 100K TPD | Must account for both phases on one model |

> **Warning:** Single-model mode has only ~10% TPD headroom. Any significant retry volume risks hitting the daily cap. Prefer dual-model where possible.

#### 2b. Python preprocessing before LLM

Not all reviews require LLM processing. Python preprocessing reduces the set **before** any API call:

| Step | Purpose |
|------|---------|
| Sort by date (latest first) | Prioritize recency |
| Apply review_limit (default: 1000) | Cap volume for rate limits |
| Remove duplicates and near-duplicates | Eliminate noise |
| Remove empty / very short reviews | Already done in Phase 1 |
| Filter spam / noise patterns | Reduce irrelevant content |
| Optionally prioritize low-rated reviews (≤2★) | Surface pain points |
| **Truncate review text for classification** | First 40 words (~50 tokens); reduces per-batch token cost (critical for single-model 70B mode) |

#### 2c. Optimized pipeline flow

```
Normalized reviews (Phase 1 output)
        │
        ▼
   Python Preprocessing (no LLM)
   ├── Sort, limit (≤1000), dedupe, filter
   └── Truncate review text to first 40 words
        │
        ▼
   Preprocessed set (≤1000 reviews, truncated)
        │
        ▼
   Batch classification
   ├── Dual-model (recommended): 8B model, batches of 25, 18s delay
   └── Single-model (fallback):   70B model, batches of 25, 10s delay
        │
        ▼
   Validate ≤5 themes ──▶ Merge overflow if needed
        │
        ▼
   Python Aggregation
   ├── Per-theme counts, avg rating, pain %
   ├── Theme score ranking
   ├── Representative quote extraction (full review text)
   └── Unmatched review logging
        │
        ▼
   themed_reviews + theme_legend + theming_report
```

#### 2d. Why 1,000 reviews (not all ~2,400)

- The latest 1,000 reviews capture the most recent and relevant user sentiment.
- Older reviews outside the active window add noise, not signal.
- 1,000 reviews at batch size 25 = 40 API calls — well within 8B daily limits.
- **70B model constraint:** 40 batches × ~2,000 tokens = ~80K TPD for Phase 2 alone. With Phase 3 needing ~10K, 1,000 reviews is the practical ceiling for single-model mode (100K TPD limit). Exceeding this would breach the daily token budget.
- Real-world product analytics teams typically sample 500–1,000 reviews per cycle.

#### 2e. Why batch size 25 (not 50)

| Factor | Batch 50 | Batch 25 |
|--------|----------|----------|
| Token usage per request | ~3,000–4,000 | ~1,500–2,000 |
| JSON parse reliability | Occasional failures | Very reliable |
| Hallucination risk | Higher | Lower |
| Recovery on failure | Lose 50 reviews | Lose only 25 |
| Fits 6K TPM (8B model) | Tight | Comfortable |
| Fits 12K TPM (70B model) | **Exceeds limit** | Comfortable with 10s delay |

| Component | Responsibility |
|-----------|----------------|
| **Python preprocessor** | Sort, limit, dedupe, filter spam — **no LLM needed** |
| **Theme legend** | 5 product themes — names, descriptions, keywords |
| **Classifier** | 8B model (recommended) or 70B model (fallback) assigns `theme_id` + `confidence` per review in batches of 25 |
| **Validator** | Cap at 5 themes; map unknown labels |
| **Aggregator** | Per-theme: count, % of total, avg rating, % low ratings, **theme score** |
| **Quote extractor** | 8B model tags representative quotes per theme |

**Theme score (for ranking in Phase 3):**

| Factor | Weight | Rationale |
|--------|--------|-----------|
| Review volume | 40% | What people talk about most |
| Low-rating share (≤2★) | 40% | Pain severity |
| Recency | 20% | What is hot this week |

#### 2f. Future scalability

- **Model swapping:** Change `model_classification` or `model_summary` in manifest without code changes.
- **Async processing:** Batch calls can be parallelized with async HTTP when rate limits allow.
- **Vector DB integration:** Embeddings can pre-cluster reviews before LLM classification.
- **Scaling beyond 10K reviews:** Add sampling strategies or move to embedding-first classification.

---


### Phase 3 — Weekly note generation

**Goal:** Executive one-pager meeting all challenge format rules.

```
Theming report + themed reviews + legend
        │
        ▼
   Rank top 3 themes
        │
        ▼
   Select quote candidates (PII-safe, faithful)
        │
        ▼
   LLM synthesize note ──▶ Validate ≤250 words ──▶ weekly_note (JSON + MD)
```

| Output section | Requirement |
|----------------|-------------|
| Top themes | Exactly **3**, with one-line summary each |
| User quotes | Exactly **3**, verbatim from reviews (minor ellipsis ok) |
| Action ideas | Exactly **3**, specific and tied to themes |
| Length | **≤250 words** total in note body |
| Tone | Executive, scannable (headings/bullets) |

**Note structure (logical):**

1. Title: Weekly Review Pulse — {product} — {week_id}
2. Top themes (3 bullets with summaries)
3. What users are saying (3 quoted lines, theme-tagged)
4. Recommended actions (3 numbered items)

**Quality rules:**

- Quotes must trace to real `review_id` in themed data.
- Re-scan for PII before saving final note.
- If over word limit: regenerate with shorten instruction (max 2 retries).

---

### Phase 4 — Google Docs (MCP)

**Goal:** Published Doc with full note; link stored for deliverables and email.

| Step | MCP action | Recorded |
|------|------------|----------|
| 1 | Create document with title template | `doc_id` |
| 2 | Write full note body | — |
| 3 | Obtain shareable link | `doc_url` |
| 4 | Write publish report | tools used, timestamp |

**Title template:** `{product} — Weekly Review Pulse — {week_id}`

**Idempotency:** Re-run for same `week_id` should **update** the same Doc (per ADR-007), not create duplicates.

**Boundary:** No Google API credentials or SDK usage in the project—MCP server handles all Google calls.

---

### Phase 5 — Gmail draft (MCP)

**Goal:** Draft email for human review; includes note and Doc link.

| Field | Template |
|-------|----------|
| To | Self or alias from manifest |
| Subject | `[Weekly Pulse] {product} — {week_id}` |
| Body | Short intro + full note + link to Doc + “Draft — review before sending” |

**Explicitly out of scope:** Send, schedule send, or mass distribution.

---

### Phase 6 — End-to-end & deliverables

**Goal:** One documented weekly path + all LIP deliverables.

| Deliverable | Source |
|-------------|--------|
| Working prototype / demo | Full run recording or walkthrough |
| Weekly note | Google Doc + local markdown copy |
| Email draft | Gmail screenshot or exported text |
| Reviews CSV | Redacted sample from Phase 1 |
| README | Re-run steps, theme legend, MCP setup |

---

## 6. Data contracts & artifacts

### 6.1 Artifact inventory per run

| Artifact | Phase | Purpose |
|----------|-------|---------|
| `run_state.json` | All | Phase completion tracking |
| `run.log` | All | Operator/agent audit trail |
| `reviews_normalized.csv` | 1 | Canonical input for theming |
| `import_report.json` | 1 | Counts, date range, redactions, errors |
| `theme_legend.json` | 2 | ≤5 themes with descriptions |
| `themed_reviews.json` | 2 | Per-review theme assignment |
| `theming_report.json` | 2 | Theme stats and scores |
| `weekly_note.json` | 3 | Structured note + metadata |
| `weekly_note.md` | 3 | Human-readable note |
| `note_report.json` | 3 | Word count, prompt version, PII scan |
| `publish_result.json` | 4 | Doc id, URL, MCP tools used |
| `docs_report.json` | 4 | Publish audit |
| `email_draft_result.json` | 5 | Draft id, subject, recipient |
| `gmail_report.json` | 5 | Draft audit |

### 6.2 `reviews_normalized.csv`

| Column | Required | Description |
|--------|----------|-------------|
| `review_id` | Yes | Stable id or hash |
| `store` | Yes | `app_store` or `play_store` |
| `rating` | Yes | 1–5 |
| `title` | No | Empty if N/A |
| `text` | Yes | PII-redacted body |
| `review_date` | Yes | ISO date |

### 6.3 `theme_legend.json`

| Field per theme | Description |
|---------------|-------------|
| `id` | Stable slug (e.g. `payments`) |
| `name` | Display name |
| `description` | What this theme covers |
| `example_keywords` | Hints for classifier |

**Constraint:** Maximum **5** themes.

### 6.4 `weekly_note.json` (logical fields)

| Field | Constraint |
|-------|------------|
| `week_id`, `product` | From manifest |
| `word_count` | ≤ 250 |
| `top_themes` | Length = 3, each with id, name, summary |
| `quotes` | Length = 3, each with text, theme_id, source_review_id |
| `action_ideas` | Length = 3, each with text, theme_id |
| `body_markdown` | Full rendered note |

### 6.5 `publish_result.json` (logical fields)

| Field | Description |
|-------|-------------|
| `status` | `success` or `failed` |
| `doc_id`, `doc_url` | Google Doc reference |
| `title` | As published |
| `published_at` | Timestamp |
| `mcp_tools_called` | Audit list |

### 6.6 `email_draft_result.json` (logical fields)

| Field | Description |
|-------|-------------|
| `status` | `success` or `failed` |
| `draft_id` | Gmail draft reference |
| `to`, `subject` | As created |
| `created_at` | Timestamp |

---

## 7. MCP integration architecture

### 7.1 Protocol stack

```
Cursor Agent  ◀──stdio/SSE──▶  MCP Server  ◀──HTTPS──▶  Google (Docs, Gmail)
```

### 7.2 Responsibilities split

| Concern | MCP server | This project |
|---------|------------|--------------|
| OAuth & tokens | Yes | No |
| Google API calls | Yes | No |
| CSV / review logic | No | Yes |
| LLM theming & note | No | Yes (agent + LLM) |
| Doc title & body content | Prepared here | Published via MCP |
| Creating Doc / draft | Yes | Triggered via MCP tools only |

### 7.3 Tool mapping (fill in Phase 0 — ADR-003)

| Our operation | MCP tool (name TBD) | Purpose |
|---------------|----------------------|---------|
| Create Doc | e.g. `create_document` | New weekly note doc |
| Write body | e.g. `append_text` / `replace_text` | Insert note content |
| Get link | e.g. `get_document` | URL for deliverable |
| Create draft | e.g. `create_draft` | Gmail draft only |

### 7.4 Phase 4 sequence (conceptual)

1. Agent reads `weekly_note.md`.
2. Agent calls MCP: create document (title from manifest).
3. Agent calls MCP: write body.
4. Agent saves `publish_result.json` with link.

### 7.5 Phase 5 sequence (conceptual)

1. Agent reads note + `doc_url`.
2. Agent calls MCP: create draft (to, subject, body).
3. Agent saves `email_draft_result.json`.
4. Human reviews in Gmail UI—**does not send from agent**.

### 7.6 MCP error handling

| Error | Action |
|-------|--------|
| Server not running | Fail Phase 4/5; note still available as markdown |
| OAuth expired | Re-authenticate via MCP server docs |
| Tool name mismatch | Update ADR-003; retry |
| Rate limit | Wait and retry (max 3) |
| Partial Doc write | Compare length; retry full replace |

---

## 8. Agent & orchestration design

### 8.1 Agent roles

| Role | Phases | Responsibility |
|------|--------|----------------|
| **Orchestrator** | All | Order, gates, fail-stop |
| **Data worker** | 1 | Import, normalize, redact |
| **Analyst** | 2 | Theme assignment |
| **Writer** | 3 | Note synthesis |
| **Publisher** | 4–5 | MCP only |

One Cursor agent with a strong system prompt can cover all roles.

### 8.2 System prompt (rules)

- Execute phases 0→5 in order; do not skip gates.
- Phases 1–3: work only in `data/runs/{week_id}/`.
- Phases 4–5: **MCP tools only** for Google Docs and Gmail.
- Enforce: ≤5 themes, ≤250 words, 3+3+3 structure, no PII.
- Email: **draft only**—never send.
- On failure: mark report failed and stop.

### 8.3 Per-phase handoff

| Phase | Agent receives | Agent produces |
|-------|----------------|----------------|
| 1 | Raw CSVs + manifest | Normalized CSV + import report |
| 2 | Normalized CSV + legend | Themed reviews + reports |
| 3 | Themed data + stats | Weekly note JSON + MD |
| 4 | Weekly note MD | Doc URL + publish report |
| 5 | Note + Doc URL | Draft confirmation + report |

---

## 9. Configuration

### 9.1 Run manifest (logical fields)

| Section | Fields |
|---------|--------|
| **Identity** | `product`, `week_id` |
| **Date range** | `start`, `end` (8–12 weeks) |
| **Inputs** | Paths to App Store and Play Store CSVs |
| **Outputs** | Run folder path |
| **Email** | `to`, subject template |
| **Docs** | Title template |
| **LLM** | See §9.3 below |
| **Theming** | Max themes (5), batch size, legend path, review_limit |

### 9.2 LLM configuration

**Dual-model (recommended):**

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `provider` | `groq` | LLM API provider |
| `model_classification` | `llama-3.1-8b-instant` | Bulk theme classification (Phase 2) |
| `model_summary` | `llama-3.3-70b-versatile` | Executive note generation (Phase 3) |
| `temperature_classification` | `0.3` | Low variance for consistent labels |
| `temperature_summary` | `0.4` | Slightly creative for natural prose |
| `classification_batch_size` | `25` | Reviews per LLM classification call |
| `review_limit` | `1000` | Max reviews to process (latest first) |
| `inter_call_delay` | `18` | Seconds between classification calls (8B TPM pacing) |

**Single-model fallback (70B only):**

| Parameter | Value | Difference from dual-model |
|-----------|-------|---------------------------|
| `model_classification` | `llama-3.3-70b-versatile` | Same model for both phases |
| `classification_batch_size` | `25` | Same |
| `review_text_truncation` | `40` words | **New** — truncates review text to save tokens |
| `inter_call_delay` | `10` | **Reduced** — 70B has higher TPM (12K vs 6K) |
| `review_limit` | `1000` | Same — cannot exceed due to TPD constraint |

### 9.3 Theme legend (Groww — fintech)

| Theme id | Name | Covers |
|----------|------|--------|
| `payments` | Payments & Transactions | UPI, withdrawals, charges, bank linking |
| `onboarding` | KYC & Verification | Signup, demat, PAN/Aadhaar, documents |
| `stability` | App Stability & UX | Crashes, lag, login, UI, general praise/complaints |
| `investments` | Mutual Funds & Investments | SIP, MF, stocks, F&O, orders, charts |
| `support` | Support & Service | Help center, chat, callbacks, resolution |

Adapt to **your LIP (4) product**.

---

## 10. Folder structure (logical)

| Folder | Purpose |
|--------|---------|
| `docs/` | Problem statement, architecture, plan, decisions, phase evals |
| `config/` | Run manifest, theme legend |
| `prompts/` | Versioned LLM prompts (theming, note) |
| `reviews_raw/` | Incoming exports (not committed if sensitive) |
| `data/runs/{week_id}/` | All artifacts for one weekly run |
| `docs/deliverables/` | Demo screenshots, sample outputs |

No implementation code required in repo for LIP—agent + artifacts + MCP suffice. Optional automation can be added later without changing this architecture.

---

## 11. Cross-cutting concerns

### 10.1 PII pipeline

```
Raw CSV → redact (Phase 1) → themed data → note (Phase 3) → scan → MCP publish (4–5)
```

**Redact:** emails, phone numbers, @handles, long numeric IDs → `[REDACTED]`.

### 10.2 LLM usage & token budget (estimated for 1,000 reviews)

#### Model assignment — Dual-model (recommended)

| Phase | Model | Calls | Est. tokens/call | Total tokens |
|-------|-------|-------|-------------------|---------------|
| 2 (classify) | `llama-3.1-8b-instant` | 40 (1000 ÷ 25) | ~1,500–2,000 | ~60K–80K |
| 3 (note) | `llama-3.3-70b-versatile` | 1–2 | ~3,000–5,000 | ~5K–10K |

#### Model assignment — Single-model fallback (70B only)

| Phase | Model | Calls | Est. tokens/call | Total tokens |
|-------|-------|-------|-------------------|---------------|
| 2 (classify, truncated) | `llama-3.3-70b-versatile` | 40 (1000 ÷ 25) | ~1,900–2,100 | ~76K–84K |
| 3 (note) | `llama-3.3-70b-versatile` | 1–2 | ~3,000–5,000 | ~5K–10K |
| **Combined** | | **41–42** | | **~81K–94K** |

> **Note:** Single-mode combined usage of ~90K leaves only ~10K TPD headroom (10%) for retries. If a batch fails and needs reprocessing, monitor cumulative tokens carefully.

#### Groq free-tier limits vs pipeline usage — Dual-model

| Limit | `8b-instant` cap | Our usage | Headroom |
|-------|-------------------|-----------|----------|
| RPM | 30 | 40 total (≤30/min with 18s pacing) | ✅ safe |
| RPD | 14,400 | 40 | ✅ 360× headroom |
| TPM | 6,000 | ~2,000 per call (serial, 18s gap) | ✅ fits with pacing |
| TPD | 500,000 | ~80,000 | ✅ 6× headroom |

| Limit | `70b-versatile` cap | Our usage (Phase 3 only) | Headroom |
|-------|----------------------|---------------------------|----------|
| RPM | 30 | 1–2 | ✅ 15× headroom |
| RPD | 1,000 | 1–2 | ✅ 500× headroom |
| TPM | 12,000 | ~5,000 | ✅ 2× headroom |
| TPD | 100,000 | ~10,000 | ✅ 10× headroom |

#### Groq free-tier limits vs pipeline usage — Single-model (70B only)

| Limit | `70b-versatile` cap | Our usage (Phase 2 + 3) | Headroom |
|-------|----------------------|--------------------------|----------|
| RPM | 30 | 40 total (≤6/min with 10s pacing) | ✅ safe |
| RPD | 1,000 | 42 | ✅ 24× headroom |
| TPM | 12,000 | ~2,000 per call (serial, 10s gap) | ✅ ~6 calls/min |
| TPD | 100,000 | ~90,000 (combined) | ⚠️ ~10% headroom only |

**Why 8B handles bulk classification well:** Theme classification is a structured, deterministic task (pick 1 of 5 labels, return JSON). The 8B model achieves near-identical accuracy to 70B for this pattern, at 5× the daily token budget — the same approach used in production AI systems at scale.

**Why 70B is reserved for summary:** Executive note synthesis requires nuanced reasoning, tone control, and creative language. The 70B model excels here but only needs 1–2 calls per weekly report.

**When single-model is necessary:** If the 8B model is unavailable or unreliable, the 70B model can handle classification at the cost of tight TPD headroom. Review text truncation (first 40 words) is essential to keep per-batch tokens low enough for the 12K TPM constraint.

### 10.3 Rate limit safety strategy

| Strategy | Implementation |
|----------|----------------|
| **Inter-request pacing (dual-model)** | 18-second delay between 8B classification batches (stays under 6K TPM: ~2K tokens ÷ 6K/min ≈ 3 calls/min → 18s gap) |
| **Inter-request pacing (single-model)** | 10-second delay between 70B classification batches (stays under 12K TPM: ~2K tokens ÷ 12K/min ≈ 6 calls/min → 10s gap) |
| **Exponential backoff** | On 429 (rate limit) errors: wait 5s → 15s → 45s, max 3 retries |
| **Token estimation** | Pre-estimate tokens per batch; skip oversized batches |
| **TPM guard** | Track cumulative tokens per minute; pause if approaching 80% of limit |
| **TPD guard (single-model)** | Track cumulative daily tokens; warn at 80K, abort at 90K to reserve budget for Phase 3 |
| **API usage logging** | Log every call: model, tokens_in, tokens_out, latency, status |
| **Batch failure isolation** | Failed batch is logged and skipped; remaining batches continue |
| **Daily budget check** | Before pipeline start, estimate total calls; abort if >80% of daily limit |
| **Review truncation (single-model)** | Truncate review text to first 40 words before sending to LLM; reduces per-call tokens by ~50% |

### 10.4 Validation layers

| Layer | What |
|-------|------|
| Phase reports | `status`, counts, errors |
| eval.md | Human sign-off per phase |
| Constraints | Automated checks where possible (theme count, word count) |

---

## 12. Security & compliance

| Topic | Approach |
|-------|----------|
| **Credentials** | Only in MCP server environment; never in git |
| **PII** | Redact at import; scan before publish |
| **Data source** | Public exports only |
| **Email** | Draft-only (ADR-006) |
| **Audit** | Retain run folder for evaluators |
| **Shared repo** | Redacted samples only |

---

## 13. Observability & debugging

### 13.1 What to log per phase

| Phase | Log |
|-------|-----|
| 1 | Row counts, filter stats, redaction counts |
| 2 | Batches processed, theme distribution |
| 3 | Word count, retries, PII scan result |
| 4–5 | MCP tools called, success/failure |

### 13.2 Debug guide

| Symptom | Likely cause | Check |
|---------|--------------|-------|
| Empty CSV after import | Date window too narrow | `import_report.json` |
| 6+ themes | LLM drift | `theming_report.json` merge log |
| Note too long | Prompt drift | `note_report.json` retries |
| Empty Doc | MCP write failed | `docs_report.json` |
| No draft | MCP / OAuth | `gmail_report.json` |

---

## 14. Phase dependencies

| Phase | Depends on | Produces | Blocks |
|-------|------------|----------|--------|
| 0 | — | MCP ready, config | 4, 5 |
| 1 | 0 (soft) | Normalized CSV | 2 |
| 2 | 1 | Themed data | 3 |
| 3 | 2 | Weekly note | 4, 5 |
| 4 | 3, 0 | Doc link | 5 (optional) |
| 5 | 3, 4 (soft) | Draft | 6 |
| 6 | 0–5 | README, demo | — |

---

## 15. Non-functional requirements

| NFR | Target |
|-----|--------|
| Operator time per week | < 15 min (excl. human email review) |
| Note length | ≤ 250 words |
| Theme cap | ≤ 5 |
| MCP reliability | Retry on transient errors |
| Reproducibility | Same legend ids week to week |

---

## 16. Failure domains & edge cases

### 16.1 By phase

| Phase | Failure | Mitigation |
|-------|---------|------------|
| 1 | Wrong CSV columns | Document header mapping; fail with clear message |
| 1 | Zero rows in window | Widen date range in manifest |
| 2 | Unknown theme label | Map to nearest canonical theme |
| 2 | >5 themes | Merge smallest into neighbors |
| 3 | Over word limit | Regenerate with shorten instruction |
| 3 | Hallucinated quote | Require source review id |
| 4 | MCP down | Keep markdown; manual paste fallback |
| 5 | Wrong recipient | Validate against manifest before MCP |

### 16.2 Edge case catalog

| # | Case | Behavior |
|---|------|----------|
| E1 | Non-English reviews | Process; no translation in v1 |
| E2 | Rating-only, no text | Drop in Phase 1 |
| E3 | Duplicate across stores | Keep richer text row |
| E4 | One theme dominates 90% | Still report top 3 by score in note |
| E5 | Re-run same week | Update same Doc (ADR-007) |

Detailed test matrices: `docs/phases/*/eval.md`.

---

## 17. CI/CD — GitHub Actions automation

### 17.1 Overview

A separate **automation layer** runs the full pipeline (Phases 1→5) on a weekly cron schedule via GitHub Actions, without modifying any phase logic. This is additive to the existing Cursor agent / manual execution modes.

```
┌──────────────────────────────────────────────────────────────┐
│                  GitHub Actions Runner                        │
│                                                               │
│  cron (Mon 09:00 UTC)  ──or──  workflow_dispatch              │
│         │                            │                        │
│         ▼                            ▼                        │
│  Validate secrets → Compute week_id → Update manifest         │
│         │                                                     │
│         ▼                                                     │
│  Fetch Play Store reviews (continue-on-error)                 │
│         │                                                     │
│         ▼                                                     │
│  Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5             │
│  (each gated on previous success; up to 3 retries per phase)  │
│         │                                                     │
│         ▼                                                     │
│  Generate weekly_summary.json + email_draft.md                │
│  Upload artifacts (30-day retention)                          │
│  Write GitHub Job Summary                                     │
│  On failure → auto-create GitHub Issue                        │
└──────────────────────────────────────────────────────────────┘
```

### 17.2 Trigger modes

| Mode | Trigger | Use case |
|------|---------|----------|
| **Scheduled** | `cron: "0 9 * * 1"` (Mondays 09:00 UTC) | Fully automated weekly runs |
| **Manual** | `workflow_dispatch` from Actions UI | On-demand runs, testing, re-runs |

### 17.3 Manual dispatch inputs

| Input | Type | Default | Purpose |
|-------|------|---------|---------|
| `week_id` | string | auto-detected | Override ISO week (e.g. `2026-W22`) |
| `through_phase` | choice 1–5 | `5` | Run only up to phase N |
| `skip_mcp` | boolean | `false` | Skip Phases 4–5 (local-only test) |

### 17.4 Required GitHub Secrets

Configure at **Settings → Secrets and variables → Actions**:

| Secret | Maps to | Required by | Notes |
|--------|---------|-------------|-------|
| `GROQ_API_KEY` | `GROQ_API_KEY` env var | Phases 2, 3 | **Required** — workflow fails fast if missing |
| `GOOGLE_DOC_ID` | `GOOGLE_DOC_ID` env var | Phase 4 | Optional if `skip_mcp=true` |
| `EMAIL_TO` | `EMAIL_TO` env var | Phase 5 | Optional if `skip_mcp=true` |
| `MCP_SERVER_URL` | `MCP_SERVER_URL` env var | Phases 4, 5 | Defaults to Railway URL if not set |

### 17.5 Artifact inventory (per run)

All artifacts are uploaded via `actions/upload-artifact@v4` with **30-day retention**.  
Bundle name: `weekly-pulse-{week_id}`.

| Artifact | Generated by | Purpose |
|----------|-------------|---------|
| `weekly_note.md` | Phase 3 | Human-readable executive note |
| `weekly_note.json` | Phase 3 | Structured note with metadata |
| `email_draft.md` | Workflow step 13 | Human-readable email preview |
| `weekly_summary.json` | Workflow step 12 | Consolidated run summary |
| `theming_report.json` | Phase 2 | Theme stats and scores |
| `import_report.json` | Phase 1 | Import counts and audit |
| `publish_result.json` | Phase 4 | Google Doc URL |
| `email_draft_result.json` | Phase 5 | Gmail draft ID |
| `run_state.json` | All phases | Phase completion tracking |
| `run.log` | All phases | Full run log |

### 17.6 Retry handling

Each phase step uses `nick-fields/retry@v3` with:

| Parameter | Value |
|-----------|-------|
| Max attempts | 3 |
| Retry wait | 30 seconds |
| Timeout per phase | 10–20 minutes |

Retries handle transient failures: Groq API 429s, MCP server hiccups, network timeouts.

### 17.7 Failure handling

| Mechanism | Behavior |
|-----------|----------|
| **Secret validation** | Fails fast with a clear message if `GROQ_API_KEY` is missing |
| **Phase gating** | Each phase only runs if the previous succeeded |
| **Retry per phase** | Up to 3 attempts with 30s backoff before marking a phase failed |
| **Timeout** | Job-level 45-minute timeout; per-phase timeouts of 10–20 min |
| **Artifact upload** | Runs on `always()` — partial artifacts preserved even on failure |
| **Failure notification** | Auto-creates a GitHub Issue with run link, week ID, and remediation steps |

### 17.8 Zero-code weekly operation

The workflow is designed to process a new week's reviews **without any code changes**:

1. `update_manifest.py` auto-computes `week_id` and 12-week date window from the current date.
2. `fetch_groww_playstore.py` refreshes the Play Store CSV automatically.
3. All phase CLIs accept `--week-id` and `--manifest` — no hardcoded values.
4. Artifact folders are namespaced by `week_id` — no collisions between runs.

---

*Implementation sequencing: [phase-wise-implementationplan.md](./phase-wise-implementationplan.md).*

