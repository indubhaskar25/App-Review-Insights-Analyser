# Phase 4 — Google Docs (MCP) — Evaluation

> **Implementation:** [Phase 4](../../phase-wise-implementationplan.md#phase-4--publish-to-google-docs-mcp) · **Architecture:** [§5.2 Docs sequence](../../architecture.md#52-phase-4--docs-publish-sequence)

---

## Purpose

Verify the weekly note is published to **Google Docs using MCP tools only**, with a stable link stored for deliverables and email.

---

## Prerequisites

- [ ] Phase 0 MCP smoke tests passed
- [ ] Phase 3 exit criteria met
- [ ] `weekly_note.md` ready for target `week_id`

---

## Test checklist

### MCP-only enforcement

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 4.1 | No direct API | `grep -r googleapiclient google.oauth2` in `src/` for Docs | No matches in Docs publish path | ☐ |
| 4.2 | Tool audit | Publish note | Only MCP tools invoked (log or Cursor tool trace) | ☐ |

### Publish flow

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 4.3 | Create doc | Run Phase 4 | Doc exists in Google Drive | ☐ |
| 4.4 | Title | Check doc title | `{product} — Weekly Review Pulse — {week_id}` | ☐ |
| 4.5 | Body content | Compare Doc to `weekly_note.md` | Full note present; formatting acceptable | ☐ |
| 4.6 | Result file | Open `publish_result.json` | Valid `doc_id`, `doc_url`, `published_at` | ☐ |
| 4.7 | Link works | Open `doc_url` in browser | Accessible to intended account | ☐ |

### Edge cases

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 4.8 | MCP down | Stop server; run Phase 4 | Fails with clear error; no partial secret leakage | ☐ |
| 4.9 | Re-run same week | Publish again | Idempotent behavior per [decision.md](../../decision.md) ADR-007 | ☐ |
| 4.10 | PII in doc | Scan published doc | No emails/usernames/IDs | ☐ |

---

## Exit criteria

- [ ] **EC-4.1** Google Doc created/updated **exclusively** via MCP
- [ ] **EC-4.2** `publish_result.json` committed or archived for demo (no secrets inside)
- [ ] **EC-4.3** Doc content matches approved `weekly_note.md` from Phase 3
- [ ] **EC-4.4** Shareable link captured for README/deliverable
- [ ] **EC-4.5** README documents MCP tool names used for Docs
- [ ] **EC-4.6** Phase 4 eval signed off

---

## Evidence to capture

- Google Doc URL (deliverable)
- MCP tool call log or screenshot from Cursor
- `publish_result.json` (redact tokens if any)

---

## Sign-off

| Field | Value |
|-------|--------|
| **Evaluator** | |
| **Date** | |
| **week_id** | |
| **doc_url** | |
| **Result** | Pass / Fail |
| **Notes** | |
