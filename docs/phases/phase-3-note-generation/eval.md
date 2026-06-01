# Phase 3 — Weekly Note Generation — Evaluation

> **Implementation:** [Phase 3](../../phase-wise-implementationplan.md#phase-3--weekly-note-generation-llm) · **Problem constraints:** [§5–6](../../problemstatement.md)

---

## Purpose

Confirm the LLM produces a **one-page weekly pulse** that meets challenge format, length, tone, and PII rules before any Google publishing.

---

## Prerequisites

- [ ] Phase 2 exit criteria met
- [ ] `themed_reviews.json` and `theme_legend.json` available

---

## Test checklist

### Structure & content

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 3.1 | Top themes | Read `weekly_note.json` | Exactly **3** themes listed in `top_themes` | ☐ |
| 3.2 | Quotes | Inspect `quotes` array | **3** quotes, verbatim from reviews (minor ellipsis ok) | ☐ |
| 3.3 | Actions | Inspect `action_ideas` | **3** actionable items tied to themes | ☐ |
| 3.4 | Word count | Run counter on `body_markdown` | **≤250 words** | ☐ |
| 3.5 | Scannability | Human read | Headings/bullets; executive tone; no jargon wall | ☐ |

### Quality (W2 skills)

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 3.6 | Quote fidelity | Compare 3 quotes to source reviews | Quotes exist in source text (post-redaction) | ☐ |
| 3.7 | Theme alignment | Quotes map to stated top themes | No obvious mismatch | ☐ |
| 3.8 | Action quality | PM review | Actions are specific, feasible, not generic fluff | ☐ |

### Safety

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 3.9 | PII scan | Search note for emails, @handles, long IDs | None found | ☐ |
| 3.10 | Regeneration | Force &gt;250 word output | Retry reduces count or fails with clear error | ☐ |

### Artifacts

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 3.11 | JSON schema | Validate `weekly_note.json` | Required fields present; `word_count` matches | ☐ |
| 3.12 | Markdown | Open `weekly_note.md` | Renders readable; matches JSON content | ☐ |

---

## Exit criteria

- [ ] **EC-3.1** `weekly_note.json` and `weekly_note.md` exist for `week_id`
- [ ] **EC-3.2** 3 themes + 3 quotes + 3 action ideas present
- [ ] **EC-3.3** Word count ≤250
- [ ] **EC-3.4** PII-free (automated scan + manual spot-check)
- [ ] **EC-3.5** Prompt version recorded (`prompts/weekly_note_v1.txt` or later)
- [ ] **EC-3.6** PM/stakeholder spot-check: “Would I send this to leadership?” → Yes

---

## Automated tests (recommended)

```
tests/test_phase3_note.py
  - test_weekly_note_schema
  - test_word_count_under_250
  - test_three_quotes_three_actions
  - test_no_email_pattern_in_body
```

---

## Evidence to capture

- Full `weekly_note.md` (for deliverable)
- `word_count` field from JSON
- Optional: side-by-side quote ↔ source review ids

---

## Sign-off

| Field | Value |
|-------|--------|
| **Evaluator** | |
| **Date** | |
| **week_id** | |
| **Word count** | |
| **Result** | Pass / Fail |
| **Notes** | |
