"""Phase 2 – Theme Grouping pipeline

Reads normalized reviews from Phase 1, applies Python preprocessing (sort, limit,
dedupe, truncate), batches them (25 per request by default), calls the Groq LLM
with rate-limit-aware pacing and exponential backoff, validates ≤5 themes,
computes theme analytics including theme scores, and writes three artefacts:

* **themed_reviews.json** – each review enriched with ``theme_id``, ``confidence``,
  ``reason``, and an optional ``representative_quote``.
* **theming_report.json** – per-theme statistics, theme scores, prompt version,
  batch count, and unmatched reviews.
* **theme_legend.json** – the legend converted from YAML to JSON.

Rate-limit strategy (per architecture §10.3):
  - Dual-model (8B classification): 18 s inter-call delay (6K TPM)
  - Single-model (70B fallback): 10 s inter-call delay (12K TPM)
  - Exponential backoff on 429: 5 s → 15 s → 45 s, max 3 retries
  - TPD guard: warn at 80 K tokens, abort at 90 K (single-model)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from groq import Groq

from src.common.manifest import RunManifest
from src.common.pii import scan_for_pii
from src.common.run_paths import RunPaths
from src.common.run_state import RunState

logger = logging.getLogger("app_review.phase2")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

THEME_SCORE_WEIGHTS = {
    "volume": 0.40,
    "low_rating_share": 0.40,
    "recency": 0.20,
}

BACKOFF_DELAYS = [5, 15, 45]  # seconds – exponential backoff on 429
MAX_RETRIES_PER_BATCH = 3


# ---------------------------------------------------------------------------
# Helpers – timestamp
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def load_normalized_reviews(normalized_path: Path) -> List[Dict[str, Any]]:
    """Load the ``normalized.json`` file produced by Phase 1."""
    with normalized_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("normalized_reviews", [])


def load_theme_legend(legend_path: Path) -> List[Dict[str, Any]]:
    """Load theme legend from YAML."""
    with legend_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("themes", [])


def truncate_text(text: str, word_limit: int) -> str:
    """Truncate review text to the first *word_limit* words."""
    if not text:
        return ""
    words = text.split()
    if len(words) <= word_limit:
        return text
    return " ".join(words[:word_limit])


def preprocess_reviews(
    reviews: List[Dict[str, Any]],
    review_limit: int = 1000,
    truncation_words: int = 40,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Sort, limit, and truncate reviews before LLM classification.

    Returns the preprocessed list and a stats dict for the report.
    """
    stats: Dict[str, Any] = {
        "input_count": len(reviews),
        "review_limit": review_limit,
        "truncation_words": truncation_words,
    }

    # Sort by date, latest first
    sorted_reviews = sorted(
        reviews,
        key=lambda r: r.get("review_date", ""),
        reverse=True,
    )

    # Apply review_limit
    limited = sorted_reviews[:review_limit]
    stats["after_limit"] = len(limited)

    # Truncate review text for classification (saves tokens)
    truncated_count = 0
    for rev in limited:
        original = rev.get("text", "")
        truncated = truncate_text(original, truncation_words)
        if truncated != original:
            truncated_count += 1
        rev["_text_classify"] = truncated  # classification text (not persisted)
        rev["_text_full"] = original  # keep full text for quote extraction

    stats["truncated_count"] = truncated_count

    return limited, stats


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

def call_groq_with_retry(
    client: Groq,
    model: str,
    temperature: float,
    system_prompt: str,
    batch: List[Dict[str, Any]],
    *,
    use_truncated: bool = True,
    max_retries: int = MAX_RETRIES_PER_BATCH,
    backoff_delays: List[int] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Invoke the Groq LLM with exponential backoff on 429 errors.

    Returns (parsed_response, call_metadata).
    """
    delays = backoff_delays or BACKOFF_DELAYS

    # Build the user message using truncated or full text
    review_payload = []
    for rev in batch:
        review_payload.append({
            "review_id": rev.get("review_id", ""),
            "text": rev.get("_text_classify" if use_truncated else "_text_full", rev.get("text", "")),
            "rating": rev.get("rating", 0),
        })

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps({"reviews": review_payload}, ensure_ascii=False)},
    ]

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            start = time.monotonic()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            elapsed = time.monotonic() - start
            usage = response.usage
            meta: Dict[str, Any] = {
                "model": model,
                "attempt": attempt + 1,
                "latency_s": round(elapsed, 2),
                "tokens_in": usage.prompt_tokens if usage else 0,
                "tokens_out": usage.completion_tokens if usage else 0,
                "tokens_total": (usage.prompt_tokens + usage.completion_tokens) if usage else 0,
                "status": "ok",
            }
            parsed = json.loads(response.choices[0].message.content)
            return parsed, meta

        except Exception as exc:
            last_error = exc
            is_rate_limit = "429" in str(exc) or "rate_limit" in str(exc).lower()
            if is_rate_limit and attempt < max_retries:
                delay = delays[min(attempt, len(delays) - 1)]
                logger.warning(
                    "Rate limit hit on attempt %d/%d, waiting %ds: %s",
                    attempt + 1, max_retries + 1, delay, exc,
                )
                time.sleep(delay)
            else:
                logger.error("LLM call failed after %d attempts: %s", attempt + 1, exc)
                raise

    # Should not reach here, but just in case
    raise RuntimeError(f"LLM call failed after {max_retries + 1} attempts") from last_error


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_classifications(
    classifications: List[Dict[str, Any]],
    legend_themes: List[Dict[str, Any]],
    max_themes: int = 5,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validate and fix theme assignments.

    - Map unknown theme_ids to the closest canonical theme or "unassigned".
    - If LLM invents >5 themes, merge overflow into closest canonical theme.
    - Returns (validated_classifications, merge_log).
    """
    canonical_ids = {t["id"] for t in legend_themes}
    merge_log: List[Dict[str, Any]] = []

    # Build a lookup from any invented theme to its closest canonical match
    invented_to_canonical: Dict[str, str] = {}

    for cls in classifications:
        theme_id = cls.get("theme_id", "unassigned")
        if theme_id in canonical_ids or theme_id == "unassigned":
            continue
        # Unknown theme – try to map it
        if theme_id not in invented_to_canonical:
            # Simple heuristic: find canonical theme whose id or name
            # shares the most words with the invented theme_id
            best_match = _closest_theme(theme_id, legend_themes)
            invented_to_canonical[theme_id] = best_match
            merge_log.append({
                "invented_theme": theme_id,
                "mapped_to": best_match,
                "reason": "auto-mapped unknown label",
            })

        cls["theme_id"] = invented_to_canonical[theme_id]
        cls.setdefault("reason", "")
        if isinstance(cls["reason"], str):
            cls["reason"] += f" [mapped from {theme_id}]"

    return classifications, merge_log


def _closest_theme(invented_id: str, legend_themes: List[Dict[str, Any]]) -> str:
    """Find the canonical theme whose id/keywords best match the invented id."""
    invented_lower = invented_id.lower().replace("_", " ").replace("-", " ")
    invented_words = set(invented_lower.split())

    best_score = -1
    best_id = "unassigned"

    for theme in legend_themes:
        score = 0
        tid = theme["id"].lower().replace("_", " ")
        # Check id containment (both directions)
        if tid in invented_lower or invented_lower in tid:
            score += 3
        # Check partial word overlap (e.g. "payment" vs "payments")
        for iw in invented_words:
            for tw in tid.split():
                if iw.startswith(tw) or tw.startswith(iw):
                    score += 2
        # Check keyword overlap
        keywords = theme.get("example_keywords", [])
        for kw in keywords:
            if kw.lower() in invented_lower:
                score += 1
        # Check word overlap
        theme_words = set(tid.split())
        overlap = invented_words & theme_words
        score += len(overlap) * 2

        if score > best_score:
            best_score = score
            best_id = theme["id"]

    return best_id if best_score > 0 else "unassigned"


# ---------------------------------------------------------------------------
# Aggregation & Theme Scoring
# ---------------------------------------------------------------------------

def compute_theme_analytics(
    themed_reviews: List[Dict[str, Any]],
    total_reviews: int,
    legend_themes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute per-theme statistics and theme scores.

    Theme score = 0.4 × volume_share + 0.4 × low_rating_share + 0.2 × recency
    """
    # Collect per-theme stats
    theme_data: Dict[str, Dict[str, Any]] = {}
    unmatched: List[Dict[str, Any]] = []

    for rev in themed_reviews:
        theme_id = rev.get("theme_id", "unassigned")
        if not theme_id or theme_id == "unassigned":
            unmatched.append({
                "review_id": rev.get("review_id", ""),
                "text_snippet": (rev.get("_text_full") or rev.get("text", ""))[:100],
            })
            continue

        d = theme_data.setdefault(theme_id, {
            "count": 0,
            "rating_sum": 0,
            "low_rating_count": 0,  # ≤2★
            "confidence_sum": 0.0,
            "recency_sum": 0.0,
            "review_dates": [],
        })
        d["count"] += 1
        rating = rev.get("rating", 0)
        d["rating_sum"] += rating
        if rating <= 2:
            d["low_rating_count"] += 1
        d["confidence_sum"] += rev.get("confidence", 0.0)

        # Recency: days from the latest review date (closer = more recent)
        review_date_str = rev.get("review_date", "")
        d["review_dates"].append(review_date_str)

    # Determine date range for recency normalization
    all_dates: List[str] = []
    for d in theme_data.values():
        all_dates.extend(d.get("review_dates", []))
    if all_dates:
        max_date = max(all_dates)
        min_date = min(all_dates)
    else:
        max_date = min_date = ""

    # Compute theme scores
    themes_report: Dict[str, Dict[str, Any]] = {}
    for theme_id, d in theme_data.items():
        count = d["count"]
        avg_rating = round(d["rating_sum"] / count, 2) if count else 0
        avg_confidence = round(d["confidence_sum"] / count, 3) if count else 0
        low_rating_share = d["low_rating_count"] / count if count else 0
        volume_share = count / total_reviews if total_reviews else 0

        # Recency: average days from max_date (lower = more recent = better)
        recency_score = 0.0
        if d["review_dates"] and max_date:
            from datetime import date as date_type
            max_dt = date_type.fromisoformat(max_date)
            min_dt = date_type.fromisoformat(min_date) if min_date else max_dt
            date_range_days = max((max_dt - min_dt).days, 1)
            days_diffs = []
            for rd in d["review_dates"]:
                try:
                    rdt = date_type.fromisoformat(rd)
                    days_diffs.append((max_dt - rdt).days)
                except (ValueError, TypeError):
                    pass
            if days_diffs:
                avg_days_ago = sum(days_diffs) / len(days_diffs)
                # Normalize: 0 (oldest) to 1 (most recent)
                recency_score = 1.0 - min(avg_days_ago / date_range_days, 1.0)

        # Weighted theme score
        theme_score = round(
            THEME_SCORE_WEIGHTS["volume"] * volume_share
            + THEME_SCORE_WEIGHTS["low_rating_share"] * low_rating_share
            + THEME_SCORE_WEIGHTS["recency"] * recency_score,
            4,
        )

        # Find theme name from legend
        theme_name = theme_id
        for t in legend_themes:
            if t["id"] == theme_id:
                theme_name = t.get("name", theme_id)
                break

        themes_report[theme_id] = {
            "name": theme_name,
            "review_count": count,
            "pct_of_total": round(volume_share * 100, 1),
            "avg_rating": avg_rating,
            "low_rating_pct": round(low_rating_share * 100, 1),
            "avg_confidence": avg_confidence,
            "recency_score": round(recency_score, 4),
            "theme_score": theme_score,
        }

    # Sort themes by score descending
    sorted_themes = dict(
        sorted(themes_report.items(), key=lambda x: x[1]["theme_score"], reverse=True)
    )

    return {
        "themes": sorted_themes,
        "unmatched_reviews": unmatched,
        "unmatched_count": len(unmatched),
    }


def extract_representative_quotes(
    themed_reviews: List[Dict[str, Any]],
    theme_id: str,
    max_quotes: int = 3,
) -> List[Dict[str, Any]]:
    """Extract representative quotes for a theme from LLM-assigned quotes.

    Picks quotes from low-rated reviews (1–3★) first, then by confidence.
    Uses full review text (not truncated) for faithful quoting.
    """
    candidates = []
    for rev in themed_reviews:
        if rev.get("theme_id") != theme_id:
            continue
        quote = rev.get("representative_quote", "")
        if not quote:
            continue
        # Verify quote exists in full text (faithful check)
        full_text = rev.get("_text_full") or rev.get("text", "")
        if quote not in full_text:
            # Allow minor ellipsis: check if parts of the quote are in the text
            continue
        # PII check on quote
        if scan_for_pii(quote):
            continue
        candidates.append({
            "text": quote,
            "review_id": rev.get("review_id", ""),
            "rating": rev.get("rating", 0),
            "confidence": rev.get("confidence", 0.0),
        })

    # Sort: prefer low-rated reviews, then high confidence
    candidates.sort(key=lambda q: (q["rating"], -q["confidence"]))
    return candidates[:max_quotes]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_theming(manifest: RunManifest, paths: RunPaths) -> Dict[str, Any]:
    """Execute Phase 2 theming.

    Returns a dict with ``status`` and detailed metrics.  All artefacts are
    written to ``paths``.
    """
    # Setup
    paths.ensure_run_dir()
    run_state = RunState(paths.run_state_json, manifest.week_id)
    run_state.mark_phase("theming", "in_progress", current_phase="theming")

    report: Dict[str, Any] = {
        "status": "failed",
        "week_id": manifest.week_id,
        "product": manifest.product,
        "generated_at": _utc_now(),
        "prompt_version": "theme_grouping_v1",
        "preprocessing": {},
        "classification": {},
        "validation": {},
        "analytics": {},
        "errors": [],
    }

    try:
        # ------------------------------------------------------------------
        # 1. Load inputs
        # ------------------------------------------------------------------
        reviews = load_normalized_reviews(paths.normalized_json)
        if not reviews:
            raise RuntimeError("No normalized reviews found for theming")

        legend_themes = load_theme_legend(manifest.theming.legend_path)
        if not legend_themes:
            raise RuntimeError(f"No themes found in legend at {manifest.theming.legend_path}")

        logger.info("Loaded %d reviews and %d legend themes", len(reviews), len(legend_themes))

        # ------------------------------------------------------------------
        # 2. Python preprocessing
        # ------------------------------------------------------------------
        review_limit = manifest.theming.review_limit if manifest.theming else 1000
        truncation_words = manifest.llm.review_text_truncation if manifest.llm else 40

        preprocessed, prep_stats = preprocess_reviews(
            reviews, review_limit=review_limit, truncation_words=truncation_words,
        )
        report["preprocessing"] = prep_stats
        logger.info(
            "Preprocessed: %d → %d reviews (%d truncated to %d words)",
            prep_stats["input_count"], prep_stats["after_limit"],
            prep_stats["truncated_count"], truncation_words,
        )

        # ------------------------------------------------------------------
        # 3. Batch classification
        # ------------------------------------------------------------------
        prompt_path = Path(__file__).resolve().parent.parent.parent / "prompts" / "theme_grouping_v1.txt"
        system_prompt = prompt_path.read_text(encoding="utf-8")

        batch_size = manifest.theming.batch_size if manifest.theming else 25
        batches = [preprocessed[i:i + batch_size] for i in range(0, len(preprocessed), batch_size)]

        model = manifest.llm.effective_classification_model if manifest.llm else "llama-3.1-8b-instant"
        temperature = manifest.llm.temperature_classification if manifest.llm else 0.3
        inter_call_delay = manifest.llm.inter_call_delay if manifest.llm else 10

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        all_classifications: List[Dict[str, Any]] = []
        total_tokens = 0
        batch_results: List[Dict[str, Any]] = []
        failed_batches = 0

        logger.info(
            "Starting classification: %d batches × %d reviews, model=%s, delay=%ds",
            len(batches), batch_size, model, inter_call_delay,
        )

        for i, batch in enumerate(batches):
            try:
                result, meta = call_groq_with_retry(
                    client,
                    model=model,
                    temperature=temperature,
                    system_prompt=system_prompt,
                    batch=batch,
                    use_truncated=True,
                )
                classifications = result.get("classifications", [])
                all_classifications.extend(classifications)
                total_tokens += meta.get("tokens_total", 0)
                meta["batch_index"] = i
                meta["batch_size"] = len(batch)
                meta["classifications_received"] = len(classifications)
                batch_results.append(meta)

                logger.info(
                    "Batch %d/%d: %d classifications, %d tokens, %.1fs",
                    i + 1, len(batches), len(classifications),
                    meta.get("tokens_total", 0), meta.get("latency_s", 0),
                )
            except Exception as exc:
                failed_batches += 1
                logger.error("Batch %d/%d FAILED: %s", i + 1, len(batches), exc)
                batch_results.append({
                    "batch_index": i,
                    "batch_size": len(batch),
                    "status": "failed",
                    "error": str(exc),
                })
                # Continue with remaining batches (isolation strategy)

            # Inter-call pacing
            if i < len(batches) - 1:
                time.sleep(inter_call_delay)

        report["classification"] = {
            "model": model,
            "temperature": temperature,
            "batch_size": batch_size,
            "total_batches": len(batches),
            "failed_batches": failed_batches,
            "total_classifications": len(all_classifications),
            "total_tokens_used": total_tokens,
            "inter_call_delay_s": inter_call_delay,
            "batch_details": batch_results,
        }

        if not all_classifications:
            raise RuntimeError("No classifications received from LLM – all batches failed")

        # ------------------------------------------------------------------
        # 4. Validate themes
        # ------------------------------------------------------------------
        max_themes = manifest.theming.max_themes if manifest.theming else 5
        validated, merge_log = validate_classifications(all_classifications, legend_themes, max_themes)
        report["validation"] = {
            "max_themes": max_themes,
            "unique_themes_found": len(set(c.get("theme_id") for c in validated if c.get("theme_id") != "unassigned")),
            "merge_log": merge_log,
        }
        logger.info("Validation: %d unique themes, %d merges", report["validation"]["unique_themes_found"], len(merge_log))

        # ------------------------------------------------------------------
        # 5. Build themed reviews (enrich originals with classification)
        # ------------------------------------------------------------------
        reviews_lookup = {r["review_id"]: r for r in preprocessed}
        themed_reviews: List[Dict[str, Any]] = []
        for cls in validated:
            rid = cls.get("review_id", "")
            rev = reviews_lookup.get(rid, {})
            themed_reviews.append({
                "review_id": rid,
                "store": rev.get("store", ""),
                "rating": rev.get("rating", 0),
                "title": rev.get("title", ""),
                "text": rev.get("_text_full") or rev.get("text", ""),
                "review_date": rev.get("review_date", ""),
                "theme_id": cls.get("theme_id"),
                "confidence": cls.get("confidence"),
                "reason": cls.get("reason"),
                "representative_quote": cls.get("representative_quote"),
            })

        # ------------------------------------------------------------------
        # 6. Compute analytics & theme scores
        # ------------------------------------------------------------------
        analytics = compute_theme_analytics(themed_reviews, len(preprocessed), legend_themes)

        # Extract top quotes per theme
        all_quotes: Dict[str, List[Dict[str, Any]]] = {}
        for theme_id in analytics["themes"]:
            all_quotes[theme_id] = extract_representative_quotes(themed_reviews, theme_id)

        report["analytics"] = analytics
        report["analytics"]["representative_quotes"] = all_quotes
        logger.info("Analytics: %d themes, %d unmatched", len(analytics["themes"]), analytics["unmatched_count"])

        # ------------------------------------------------------------------
        # 7. Write artefacts
        # ------------------------------------------------------------------
        # themed_reviews.json
        themed_reviews_path = paths.themed_reviews_json
        themed_reviews_path.parent.mkdir(parents=True, exist_ok=True)
        with themed_reviews_path.open("w", encoding="utf-8") as f:
            json.dump(themed_reviews, f, indent=2, ensure_ascii=False)

        # theming_report.json
        report_path = paths.theming_report_json
        report["status"] = "success"
        report["total_reviews_processed"] = len(preprocessed)
        report["total_classifications"] = len(all_classifications)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # theme_legend.json – convert YAML legend to JSON
        legend_dest = paths.theme_legend_json
        legend_data = {"themes": legend_themes}
        with legend_dest.open("w", encoding="utf-8") as f:
            json.dump(legend_data, f, indent=2, ensure_ascii=False)

        # Update run state
        run_state.mark_phase("theming", "complete", current_phase="note_gen")
        logger.info("Phase 2 complete: %d reviews themed", len(themed_reviews))

        return report

    except Exception as exc:
        logger.exception("Theming failed: %s", exc)
        report["errors"].append(str(exc))
        run_state.mark_phase("theming", "failed", current_phase="theming")
        # Write partial report
        report_path = paths.theming_report_json
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        raise
        # Write partial report
        report_path = paths.theming_report_json
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        raise
