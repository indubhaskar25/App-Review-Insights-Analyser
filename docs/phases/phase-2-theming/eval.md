# Phase 2 — Theme Grouping — Evaluation

> **Implementation:** [Phase 2](../../phase-wise-implementationplan.md#phase-2--theme-grouping-5-themes) · **Architecture:** [§3.2 Data Layer](../../architecture.md#32-data--processing-layer-phases-13)

---

## Purpose

Verify reviews are assigned to **at most 5 themes** with a clear legend suitable for README and weekly note generation.

---

## Prerequisites

- [ ] Phase 1 exit criteria met
- [ ] `reviews_normalized.csv` for target `week_id`

---

## Test checklist

### Functional

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 2.1 | Theme count | Run theming | ≤5 distinct `theme_id` values in output | ☐ |
| 2.2 | Full coverage | Compare row counts | Every imported review has a theme label (or explicit `unassigned` policy documented) | ☐ |
| 2.3 | Legend | Open `theme_legend.json` | Each theme has `id`, `name`, `description` | ☐ |
| 2.4 | Product fit | Review legend names | Themes match your LIP (4) product domain (e.g., KYC, payments) | ☐ |
| 2.5 | Stability | Re-run same input | Same legend ids (deterministic or documented variance) | ☐ |

### Quality

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 2.6 | Spot-check 15 | Manual read of 15 assignments | ≥12/15 clearly correct | ☐ |
| 2.7 | Imbalance | Check distribution | No single theme &gt;80% unless justified in report | ☐ |
| 2.8 | Low-rating signal | Per-theme avg rating in report | Themes with pain points visible in metrics | ☐ |

### Edge cases

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 2.9 | LLM proposes 6+ themes | Force or simulate | Pipeline caps/merges to 5; logged in `theming_report.json` | ☐ |
| 2.10 | Very short review | `"ok"` only | Assigned to reasonable theme or `general` bucket | ☐ |
| 2.11 | Non-English review | If present in data | Still assigned; no crash | ☐ |

---

## Exit criteria

- [ ] **EC-2.1** `theme_legend.json` and `themed_reviews.json` exist for `week_id`
- [ ] **EC-2.2** **≤5** themes in legend
- [ ] **EC-2.3** `theming_report.json` includes per-theme counts and avg rating
- [ ] **EC-2.4** Theme legend copied or linked in README (draft acceptable)
- [ ] **EC-2.5** Spot-check pass rate ≥80% (12/15)
- [ ] **EC-2.6** No PII introduced in legend or themed JSON

---

## Automated tests (recommended)

```
tests/test_phase2_theming.py
  - test_theme_count_never_exceeds_five
  - test_every_review_has_theme
  - test_legend_schema_valid
```

---

## Evidence to capture

- `theming_report.json` theme distribution table
- Screenshot or excerpt of `theme_legend.json` (names only)

---

## Sign-off

| Field | Value |
|-------|--------|
| **Evaluator** | |
| **Date** | |
| **week_id** | |
| **Theme count** | |
| **Result** | Pass / Fail |
| **Notes** | |
