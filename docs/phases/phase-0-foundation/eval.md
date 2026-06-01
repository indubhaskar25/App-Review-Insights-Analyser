# Phase 0 — Foundation & MCP Setup — Evaluation

> **Implementation:** [Phase 0](../../phase-wise-implementationplan.md#phase-0--foundation--mcp-setup) · **Architecture:** [§5 MCP Integration](../../architecture.md#5-mcp-integration-architecture)

---

## Purpose

Confirm the repo, run manifest, and **Google Workspace MCP server** are ready before any review data processing.

---

## Prerequisites

- [ ] Google account with access to Docs and Gmail
- [ ] MCP server package chosen and documented in [decision.md](../../decision.md) (ADR-003)
- [ ] Cursor (or MCP client) installed

---

## Test checklist

### MCP connectivity

| # | Test | Steps | Pass? |
|---|------|-------|-------|
| 0.1 | Server starts | Launch MCP server via config; no auth errors in logs | ☐ |
| 0.2 | Docs tool | Create doc `MCP Smoke Test — delete me` | ☐ |
| 0.3 | Docs write | Append or replace text in smoke doc | ☐ |
| 0.4 | Gmail draft | Create draft to self/alias with subject `MCP Smoke Test` | ☐ |
| 0.5 | Draft visible | Open Gmail → Drafts; draft exists | ☐ |

### Repository scaffold

| # | Test | Steps | Pass? |
|---|------|-------|-------|
| 0.6 | Directory layout | `config/`, `prompts/`, `data/runs/`, `reviews_raw/` exist | ☐ |
| 0.7 | Run manifest | `config/run_manifest.yaml` has `product`, `week_id`, date range, `recipient` | ☐ |
| 0.8 | No secrets in git | `.env` / credentials gitignored; README lists env var **names** only | ☐ |
| 0.9 | Runner skeleton | `scripts/run_weekly.py` exists (may be no-op) | ☐ |

### Documentation

| # | Test | Steps | Pass? |
|---|------|-------|-------|
| 0.10 | ADR-001 | [decision.md](../../decision.md) states MCP-only for Docs/Gmail | ☐ |
| 0.11 | Tool mapping | ADR-003 table filled with actual MCP tool names | ☐ |

---

## Exit criteria (must all pass)

- [ ] **EC-0.1** MCP server runs without error in the target environment (Cursor)
- [ ] **EC-0.2** At least one Google Doc created **only** via MCP tools
- [ ] **EC-0.3** At least one Gmail draft created **only** via MCP tools
- [ ] **EC-0.4** No `google-api-python-client` (or similar) imports in repo for Docs/Gmail
- [ ] **EC-0.5** `config/run_manifest.yaml` committed with sane defaults
- [ ] **EC-0.6** Phase 0 eval checklist completed and dated below

---

## Evidence to capture

- Screenshot or log snippet: MCP tool success for Doc + draft
- Link to smoke-test Doc (optional; delete after)
- Screenshot of Gmail draft folder

---

## Sign-off

| Field | Value |
|-------|--------|
| **Evaluator** | |
| **Date** | |
| **MCP server used** | |
| **Result** | Pass / Fail |
| **Notes** | |
