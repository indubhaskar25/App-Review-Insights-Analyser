# Phase 6 — E2E Orchestration & Deliverables — Evaluation

> **Implementation:** [Phase 6](../../phase-wise-implementationplan.md#phase-6--end-to-end-orchestration--deliverables) · **Problem deliverables:** [§7](../../problemstatement.md)

---

## Purpose

Confirm the **full weekly workflow** runs end-to-end, is documented for re-run, and meets all challenge deliverables.

---

## Prerequisites

- [ ] Phases 0–5 exit criteria met (or documented exceptions)
- [ ] README draft exists

---

## Test checklist

### End-to-end run

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 6.1 | Fresh week | New `week_id` + new CSVs | Phases 1→5 complete without manual copy-paste | ☐ |
| 6.2 | Artifacts | List `data/runs/{week_id}/` | All expected JSON/CSV/MD files present | ☐ |
| 6.3 | Doc link | From README or publish result | Working Google Doc | ☐ |
| 6.4 | Gmail draft | Inbox check | Draft ready for human send | ☐ |
| 6.5 | Timing | Measure run | Completes in reasonable time (&lt;15 min operator) | ☐ |

### Deliverables (challenge)

| # | Deliverable | Check | Pass? |
|---|-------------|-------|-------|
| 6.6 | Prototype / demo | Link or ≤3 min video recorded | ☐ |
| 6.7 | Weekly note | PDF/Doc/MD available | ☐ |
| 6.8 | Email draft | Screenshot or text in repo/docs | ☐ |
| 6.9 | Reviews CSV | Sample/redacted CSV in repo | ☐ |
| 6.10 | README | Re-run steps + theme legend + MCP setup | ☐ |

### Constraints regression

| # | Constraint | Verification | Pass? |
|---|------------|--------------|-------|
| 6.11 | ≤5 themes | Legend + note | ☐ |
| 6.12 | ≤250 words | Note word count | ☐ |
| 6.13 | No PII | All public artifacts | ☐ |
| 6.14 | Public exports only | No scraper credentials in repo | ☐ |
| 6.15 | MCP only for Google | Code review + ADR-001 | ☐ |

### Documentation

| # | Test | Expected | Pass? |
|---|------|----------|-------|
| 6.16 | Weekly re-run | README section: drop CSV → command → MCP steps | ☐ |
| 6.17 | Theme legend | Table in README matches `theme_legend.json` | ☐ |
| 6.18 | MCP server | Name, install, env vars documented | ☐ |
| 6.19 | Decisions | ADR-002, ADR-003, ADR-004, ADR-005 filled (not Proposed) | ☐ |

---

## Exit criteria (project complete)

- [ ] **EC-6.1** One full E2E run documented with `week_id` example
- [ ] **EC-6.2** All problem-statement deliverables checked off (6.6–6.10)
- [ ] **EC-6.3** All phase evals 0–5 signed Pass
- [ ] **EC-6.4** Evaluator can re-run following README alone
- [ ] **EC-6.5** Demo video or prototype link submitted

---

## Demo script (≤3 min) — suggested flow

1. Show `reviews_raw/` CSVs and manifest (10s)
2. Run orchestrator / agent (30s)
3. Show `weekly_note.md` + theme counts (30s)
4. Open Google Doc (30s)
5. Show Gmail draft (20s)
6. Point to README re-run section (20s)

---

## Evidence to capture

- Demo video URL or prototype link
- README link in repo
- Checklist table of all phase sign-offs

---

## Sign-off

| Field | Value |
|-------|--------|
| **Evaluator** | |
| **Date** | |
| **Demo link** | |
| **E2E week_id** | |
| **Result** | Pass / Fail |
| **Notes** | |
