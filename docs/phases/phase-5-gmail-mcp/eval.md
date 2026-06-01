# Phase 5 — Gmail Draft (MCP) — Evaluation

> **Implementation:** [Phase 5](../../phase-wise-implementationplan.md#phase-5--gmail-draft-mcp) · **Architecture:** [§5.3 Gmail sequence](../../architecture.md#53-phase-5--gmail-draft-sequence)

---

## Purpose

Verify a **Gmail draft** is created via MCP containing the weekly note (and optional Doc link), without auto-send.

---

## Prerequisites

- [ ] Phase 0 MCP smoke tests passed
- [ ] Phase 3 exit criteria met
- [ ] Phase 4 recommended (for doc link in body)
- [ ] Recipient alias configured in `run_manifest.yaml`

---

## Test checklist

### MCP-only enforcement

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 5.1 | No direct API | `grep -r googleapiclient` in Gmail path | No Gmail REST from app code | ☐ |
| 5.2 | Tool audit | Create draft | Only MCP `create_draft` (or equivalent) used | ☐ |

### Draft content

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 5.3 | Draft exists | Gmail → Drafts | New draft visible | ☐ |
| 5.4 | Recipient | Check To field | Self or configured alias | ☐ |
| 5.5 | Subject | Read subject | `[Weekly Pulse] {product} — {week_id}` | ☐ |
| 5.6 | Body | Read body | Weekly note + optional Doc URL | ☐ |
| 5.7 | Not sent | Sent folder | Email **not** in Sent (draft only) | ☐ |
| 5.8 | Result file | `email_draft_result.json` | `draft_id`, `subject`, `to` populated | ☐ |

### Safety

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 5.9 | PII | Scan draft body | No usernames/emails/IDs | ☐ |
| 5.10 | Wrong recipient | Misconfigure manifest (test env) | Validation blocks or warns before MCP call | ☐ |

---

## Exit criteria

- [ ] **EC-5.1** Gmail draft created **exclusively** via MCP
- [ ] **EC-5.2** Draft recipient matches manifest
- [ ] **EC-5.3** Subject and body match template; note content consistent with Phase 3
- [ ] **EC-5.4** Email **not** auto-sent (ADR-006)
- [ ] **EC-5.5** Screenshot or pasted text captured for deliverable
- [ ] **EC-5.6** `email_draft_result.json` saved under `data/runs/{week_id}/`
- [ ] **EC-5.7** Phase 5 eval signed off

---

## Evidence to capture

- Screenshot of Gmail draft (To, Subject, body excerpt)
- `email_draft_result.json` snippet

---

## Sign-off

| Field | Value |
|-------|--------|
| **Evaluator** | |
| **Date** | |
| **week_id** | |
| **draft_id** | |
| **Result** | Pass / Fail |
| **Notes** | |
