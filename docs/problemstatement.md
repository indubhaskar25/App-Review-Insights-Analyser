# App Review Insights Analyser

> **Project Domain:** Product Analytics · LLM Workflows · AI Automation  
> **Challenge:** LIP (4) — continuation of your chosen product from the previous LIP  
> **Integration Model:** Google Workspace via **MCP server** (not direct Google APIs)  
> **Example product (this repo):** [Groww](https://groww.in) — using publicly available App Store and Play Store reviews for **educational and portfolio purposes** only. **Not affiliated with Groww**; no official partnership or internal data access.

---

## 1. Problem Statement

Product, growth, and support teams need a reliable weekly pulse on what users are saying in app stores—but manually reading hundreds of reviews across App Store and Play Store is slow, inconsistent, and easy to deprioritize.

**This project asks you to build an automated workflow** that ingests recent public reviews, clusters them into a small set of themes, and produces a scannable one-page weekly note with real quotes and concrete action ideas. The note must be written to **Google Docs**, and a **Gmail draft** must be created so you can review and send it yourself.

You should use the **same product/app you selected in LIP challenge (4)** so themes and quotes stay grounded in your real user base.

---

## 2. Objective

Design and implement an end-to-end pipeline that:

| # | Stage | Description |
|---|--------|-------------|
| 1 | **Import** | Load 8–12 weeks of App Store + Play Store reviews (rating, title, text, date) from public exports |
| 2 | **Group** | Cluster reviews into **at most 5 themes** (e.g., onboarding, KYC, payments, statements, withdrawals) |
| 3 | **Generate note** | Produce a one-page weekly pulse: top 3 themes, 3 user quotes, 3 action ideas (≤250 words, no PII) |
| 4 | **Publish** | Create/update the weekly note in **Google Docs** via MCP |
| 5 | **Draft email** | Create a **Gmail draft** containing the note (to yourself or an alias) via MCP |

---

## 3. Who This Helps

| Audience | Value |
|----------|--------|
| **Product / Growth** | See what to fix or double down on next |
| **Support** | Align responses with recurring user language |
| **Leadership** | Quick weekly health pulse without reading raw reviews |

---

## 4. Google Workspace Integration (Required: MCP)

**Do not integrate Google Docs or Gmail through direct REST/SDK calls** (e.g., `google-api-python-client`, OAuth flows wired only in application code, or manual `curl` to Google endpoints).

All Google Docs and Gmail operations must go through a **configured MCP server** that exposes tools the agent (or your orchestration layer) can call—for example:

- **Google Docs:** create document, append/replace content, export or link the latest weekly note
- **Gmail:** compose draft, set subject/body/recipients, leave as draft (send to yourself/alias for review)

### Why MCP

- Keeps auth and Google API surface area inside the MCP server, not scattered across your app
- Matches the **W3 — AI Workflow Automations** pattern: LLM/agent steps chained with tool calls
- Makes the prototype reproducible in Cursor (or any MCP client) with the same tool contract each week

### Setup expectations

- Configure the MCP server in your environment (e.g., Cursor `mcp.json`) with credentials/scopes the server requires
- Document in the README which MCP server you used and how to re-run the workflow for a new week
- If a tool is unavailable, fail clearly in logs/output—do not fall back to embedding raw Google API keys in application code

---

## 5. What You Must Build

1. **Review import** — Last **8–12 weeks** from public App Store / Play Store exports (CSV or equivalent). Fields: rating, title, text, date. Normalization rules: keep reviews with > 6 words, remove reviews with emojis, keep only English language reviews.
2. **Theming** — Group into **≤5 themes**; document your theme legend in the README.
3. **Weekly one-page note** containing:
   - Top **3 themes** (from your grouping)
   - **3 real user quotes** (redacted if needed; no usernames/emails/IDs)
   - **3 action ideas** tied to themes
4. **Google Docs artifact** — Weekly note stored as a Doc (created/updated via MCP).
5. **Gmail draft** — Email body includes the note; recipient is yourself or an alias (via MCP).
6. **PII hygiene** — No usernames, emails, or device/account IDs in the note, email, or shared samples.

---

## 6. Key Constraints

| Constraint | Detail |
|------------|--------|
| **Data source** | Public review exports only — no scraping behind logins |
| **Themes** | Maximum **5** theme buckets |
| **Note length** | Scannable, **≤250 words** |
| **PII** | No usernames, emails, or IDs in any deliverable |
| **Google access** | **MCP tools only** for Docs and Gmail — not standalone Google API integration in app code |

---

## 7. Deliverables

| Deliverable | Notes |
|-------------|--------|
| **Working prototype** | Runnable link or ≤3 min demo video |
| **Latest weekly note** | Google Doc link (or PDF/MD export of the same content) |
| **Email draft** | Screenshot or pasted draft text showing MCP-created draft |
| **Reviews CSV** | File used for the run (sample/redacted acceptable) |
| **README** | How to re-run for a new week; theme legend; **MCP server name and config steps** |

---

## 8. End-to-End Workflow

```
┌─────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Import    │───▶│   Group     │───▶│  Generate Note   │───▶│  Google Docs    │───▶│  Gmail Draft    │
│  (CSV/API   │    │  (≤5 themes)│    │  (LLM summary)   │    │  (MCP tools)    │    │  (MCP tools)    │
│   export)   │    │             │    │                  │    │                 │    │                 │
└─────────────┘    └─────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 9. Skills Being Tested

### W2 — LLMs & Prompting

- Summarization across many reviews
- Quote selection (faithful, on-theme, PII-safe)
- Tone control (executive-ready, scannable)

### W3 — AI Workflow Automations

- **Import → Group → Generate Note → Publish (Docs) → Draft Email**
- Tool use via **MCP** for external systems (Google Docs, Gmail)
- Repeatable weekly re-run documented in README

---

## 10. Out of Scope (Unless You Extend Voluntarily)

- Sending email without human review (draft only is required)
- Private or authenticated app-store scraping
- Direct Google Calendar, Drive, or Sheets API integration in application code (use MCP if you need those surfaces)
