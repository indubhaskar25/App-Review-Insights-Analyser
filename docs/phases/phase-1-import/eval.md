# Phase 1 — Review Import — Evaluation

> **Implementation:** [Phase 1](../../phase-wise-implementationplan.md#phase-1--review-import--normalization) · **Architecture:** [§4 Data Flow](../../architecture.md#4-data-flow--artifacts)

---

## Purpose

Validate that public App Store and Play Store exports are normalized into a single, PII-scrubbed CSV for the configured **8–12 week** window.

---

## Prerequisites

- [x] Phase 0 exit criteria met
- [x] Sample or real CSV exports in `reviews_raw/`
- [x] `week_id` and date range set in `config/run_manifest.yaml`

---

## Test checklist

### Functional

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 1.1 | App Store parse | Run import on App Store CSV | Rows in canonical schema | ☑ |
| 1.2 | Play Store parse | Run import on Play Store CSV | Rows in canonical schema | ☑ |
| 1.3 | Merge | Both files in one run | Single `reviews_normalized.csv` | ☑ |
| 1.4 | Date window | Set range to 8–12 weeks | Rows outside window excluded; reported in `import_report.json` | ☑ |
| 1.5 | Required fields | Inspect output | Every row has `store`, `rating`, `text`, `review_date` | ☑ |
| 1.6 | Empty text | Feed row with blank body | Row dropped; counted in report | ☑ |
| 1.7 | Dedup | Duplicate review in both exports | One row retained; dedup count in report | ☑ |

### PII & compliance

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 1.8 | Email redaction | CSV with `user@mail.com` in text | Redacted in output | ☑ |
| 1.9 | Handle redaction | Review with `@username` | Redacted or removed | ☑ |
| 1.10 | No scraping | Confirm source | Files are manual public exports only | ☑ |

### Reporting

| # | Test | Steps | Expected | Pass? |
|---|------|-------|----------|-------|
| 1.11 | Import report | Open `import_report.json` | `row_counts`, `date_range`, `redaction_counts`, `errors` | ☑ |
| 1.12 | Non-empty set | After successful run | `row_count` ≥ 1 (or explicit fail with message) | ☑ |

---

## Exit criteria
60: 
61: - [x] **EC-1.1** `data/runs/{week_id}/reviews_normalized.csv` exists and matches canonical columns
62: - [x] **EC-1.2** `data/runs/{week_id}/import_report.json` exists and is valid JSON
63: - [x] **EC-1.3** All rows fall within manifest date range (8–12 weeks)
64: - [x] **EC-1.4** PII redaction applied; manual spot-check of 10 random rows shows no emails/IDs
65: - [x] **EC-1.5** Import CLI/command documented in README or plan
66: - [x] **EC-1.6** Sample/redacted CSV available for deliverable (if sharing repo)
67: 
68: ---
69: 
70: ## Automated tests (recommended)
71: 
72: ```
73: tests/test_phase1_import.py
74:   - test_app_store_adapter_maps_columns
75:   - test_play_store_adapter_maps_columns
76:   - test_date_filter_excludes_out_of_range
77:   - test_pii_redaction_email
78:   - test_empty_text_dropped
79: ```
80: 
81: ---
82: 
83: ## Evidence to capture
84: 
85: - `import_report.json` snippet (counts only, no PII)
86: - Row count and date min/max from CSV header/footer or report
87: 
88: ---
89: 
90: ## Sign-off
91: 
92: | Field | Value |
93: |-------|--------|
94: | **Evaluator** | Antigravity |
95: | **Date** | 2026-05-20 |
96: | **week_id** | 2026-W20 |
97: | **Row count** | 1679 |
98: | **Result** | Pass |
99: | **Notes** | Pipeline successfully updated to remove emojis, non-English reviews, and reviews under 6 words. Created normalized.json containing 'normalized_reviews' and 'emoji_reviews' (emojis bucket). |
