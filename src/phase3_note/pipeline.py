"""Phase 3 – Weekly Note Generation pipeline

Reads theming artefacts from Phase 2 (theming_report.json, themed_reviews.json,
theme_legend.json), selects top 3 themes by score, picks PII-safe representative
quotes, calls the Groq LLM (70B model by default) to synthesize an executive
weekly pulse note, validates the output (≤250 words, 3 + 3 + 3 structure,
no PII), and writes three artefacts:

* **weekly_note.json** – structured note with top_themes, quotes, action_ideas,
  and body_markdown.
* **weekly_note.md** – human-readable markdown version.
* **note_report.json** – word count, prompt version, PII scan result, retries.

Rate-limit strategy (per architecture §10.2–10.3):
  - Phase 3 uses model_summary (default: llama-3.3-70b-versatile), 1–2 calls only.
  - 70B budget: ~5K–10K tokens, well within 100K TPD / 30 RPM / 12K TPM.
  - Exponential backoff on 429: 5 s → 15 s → 45 s, max 3 retries.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

from src.common.manifest import RunManifest
from src.common.pii import scan_for_pii
from src.common.run_paths import RunPaths
from src.common.run_state import RunState

logger = logging.getLogger("app_review.phase3")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_WORDS = 250
MAX_RETRIES = 2  # regeneration retries for over-word-limit
BACKOFF_DELAYS = [5, 15, 45]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def count_words(text: str) -> int:
    """Count words in text (splits on whitespace)."""
    return len(text.split())


# ---------------------------------------------------------------------------
# Load Phase 2 artefacts
# ---------------------------------------------------------------------------

def load_theming_report(path: Path) -> Dict[str, Any]:
    """Load theming_report.json from Phase 2."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_themed_reviews(path: Path) -> List[Dict[str, Any]]:
    """Load themed_reviews.json from Phase 2."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_theme_legend_json(path: Path) -> List[Dict[str, Any]]:
    """Load theme_legend.json from Phase 2 output."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("themes", [])


# ---------------------------------------------------------------------------
# Theme ranking & quote selection
# ---------------------------------------------------------------------------

def select_top_themes(
    theming_report: Dict[str, Any],
    n: int = 3,
) -> List[Dict[str, Any]]:
    """Select the top *n* themes by theme_score from the theming report.

    Returns a list of dicts with keys: id, name, review_count, avg_rating,
    low_rating_pct, theme_score.
    """
    themes_data = theming_report.get("analytics", {}).get("themes", {})
    if not themes_data:
        raise RuntimeError("No theme analytics found in theming report")

    # themes_data is already sorted by theme_score desc (from Phase 2)
    ranked = []
    for tid, tinfo in themes_data.items():
        ranked.append({
            "id": tid,
            "name": tinfo.get("name", tid),
            "review_count": tinfo.get("review_count", 0),
            "avg_rating": tinfo.get("avg_rating", 0),
            "low_rating_pct": tinfo.get("low_rating_pct", 0),
            "theme_score": tinfo.get("theme_score", 0),
        })

    return ranked[:n]


def select_quote_candidates(
    theming_report: Dict[str, Any],
    themed_reviews: List[Dict[str, Any]],
    top_theme_ids: List[str],
    quotes_per_theme: int = 3,
) -> Dict[str, List[Dict[str, Any]]]:
    """Select PII-safe, faithful quote candidates for each top theme.

    Uses representative_quotes from theming_report when available,
    falling back to scanning themed_reviews for representative_quote fields.
    """
    # Try using the pre-computed quotes from theming report
    pre_computed = theming_report.get("analytics", {}).get("representative_quotes", {})

    result: Dict[str, List[Dict[str, Any]]] = {}

    for theme_id in top_theme_ids:
        candidates: List[Dict[str, Any]] = []

        # 1. Use pre-computed quotes if available
        if theme_id in pre_computed and pre_computed[theme_id]:
            for q in pre_computed[theme_id]:
                text = q.get("text", "")
                if not text:
                    continue
                # PII scan
                if scan_for_pii(text):
                    logger.warning("Skipping PII-containing quote for theme %s", theme_id)
                    continue
                candidates.append({
                    "text": text,
                    "source_review_id": q.get("review_id", ""),
                    "rating": q.get("rating", 0),
                    "theme_id": theme_id,
                })

        # 2. Fall back to themed_reviews if not enough candidates
        if len(candidates) < quotes_per_theme:
            review_ids_seen = {c["source_review_id"] for c in candidates}
            for rev in themed_reviews:
                if rev.get("theme_id") != theme_id:
                    continue
                rid = rev.get("review_id", "")
                if rid in review_ids_seen:
                    continue
                quote = rev.get("representative_quote", "")
                if not quote:
                    continue
                if scan_for_pii(quote):
                    continue
                # Verify faithfulness: quote must appear in full text
                full_text = rev.get("text", "")
                if quote not in full_text:
                    continue
                candidates.append({
                    "text": quote,
                    "source_review_id": rid,
                    "rating": rev.get("rating", 0),
                    "theme_id": theme_id,
                })
                review_ids_seen.add(rid)
                if len(candidates) >= quotes_per_theme:
                    break

        # Sort: prefer low-rated reviews (pain signals)
        candidates.sort(key=lambda q: (q["rating"],))
        result[theme_id] = candidates[:quotes_per_theme]

    return result


# ---------------------------------------------------------------------------
# LLM note generation
# ---------------------------------------------------------------------------

def call_groq_note(
    client: Groq,
    model: str,
    temperature: float,
    system_prompt: str,
    user_payload: Dict[str, Any],
    *,
    max_retries: int = 3,
    backoff_delays: List[int] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Invoke the Groq LLM for note generation with retry on 429.

    Returns (parsed_response, call_metadata).
    """
    delays = backoff_delays or BACKOFF_DELAYS

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
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

    raise RuntimeError(f"LLM call failed after {max_retries + 1} attempts") from last_error


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_note(note: Dict[str, Any], themed_reviews: List[Dict[str, Any]]) -> List[str]:
    """Validate a generated note against architecture constraints.

    Returns list of issues found (empty = valid).
    """
    issues: List[str] = []

    # Check required sections
    top_themes = note.get("top_themes", [])
    quotes = note.get("quotes", [])
    actions = note.get("action_ideas", [])
    body = note.get("body_markdown", "")

    if len(top_themes) != 3:
        issues.append(f"Expected 3 top_themes, got {len(top_themes)}")
    if len(quotes) != 3:
        issues.append(f"Expected 3 quotes, got {len(quotes)}")
    if len(actions) != 3:
        issues.append(f"Expected 3 action_ideas, got {len(actions)}")

    # Word count
    word_count = count_words(body)
    if word_count > MAX_WORDS:
        issues.append(f"Note body is {word_count} words (limit: {MAX_WORDS})")

    # PII scan on body
    pii_found = scan_for_pii(body)
    if pii_found:
        issues.append(f"PII detected in body: {pii_found}")

    # Quote traceability — each quote must reference a real review_id
    review_ids = {r.get("review_id", "") for r in themed_reviews}
    for q in quotes:
        src = q.get("source_review_id", "")
        if src and src not in review_ids:
            issues.append(f"Quote references unknown review_id: {src}")

    # PII scan on individual quotes
    for i, q in enumerate(quotes):
        pii = scan_for_pii(q.get("text", ""))
        if pii:
            issues.append(f"Quote {i + 1} contains PII: {pii}")

    return issues


def validate_quotes_against_source(
    quotes: List[Dict[str, Any]],
    themed_reviews: List[Dict[str, Any]],
) -> List[str]:
    """Check that each quote text appears verbatim in its source review.

    Returns list of issues.
    """
    issues: List[str] = []
    review_map = {r.get("review_id", ""): r for r in themed_reviews}

    for i, q in enumerate(quotes):
        src_id = q.get("source_review_id", "")
        text = q.get("text", "")
        rev = review_map.get(src_id)
        if not rev:
            continue  # already flagged in validate_note
        full_text = rev.get("text", "")
        # Allow minor ellipsis: check if the quote text (minus "..." parts)
        # appears in the source
        if text not in full_text:
            # Try with ellipsis normalization
            normalized_quote = re.sub(r"\.\.\.+", "...", text)
            normalized_source = re.sub(r"\.\.\.+", "...", full_text)
            if normalized_quote not in normalized_source:
                issues.append(f"Quote {i + 1} not found verbatim in source review {src_id}")

    return issues


# ---------------------------------------------------------------------------
# Build LLM prompt payload
# ---------------------------------------------------------------------------

def build_note_payload(
    top_themes: List[Dict[str, Any]],
    quote_candidates: Dict[str, List[Dict[str, Any]]],
    product: str,
    week_id: str,
) -> Dict[str, Any]:
    """Build the user message payload for the note generation LLM call."""
    # Build themes input
    themes_input = []
    for t in top_themes:
        themes_input.append({
            "id": t["id"],
            "name": t["name"],
            "review_count": t["review_count"],
            "avg_rating": t["avg_rating"],
            "low_rating_pct": t["low_rating_pct"],
            "theme_score": t["theme_score"],
        })

    # Build quotes input — pick best quote per theme (one per theme for 3 total)
    quotes_input = []
    for t in top_themes:
        tid = t["id"]
        candidates = quote_candidates.get(tid, [])
        if candidates:
            best = candidates[0]  # already sorted by low-rating first
            quotes_input.append({
                "text": best["text"],
                "source_review_id": best["source_review_id"],
                "rating": best["rating"],
                "theme_id": tid,
            })

    return {
        "product": product,
        "week_id": week_id,
        "top_themes": themes_input,
        "quotes": quotes_input,
        "constraints": {
            "max_words": MAX_WORDS,
            "num_themes": 3,
            "num_quotes": 3,
            "num_actions": 3,
        },
    }


# ---------------------------------------------------------------------------
# Render markdown from structured note
# ---------------------------------------------------------------------------

def render_note_markdown(note: Dict[str, Any], product: str, week_id: str) -> str:
    """Render the weekly note as markdown from structured fields.

    Uses body_markdown from LLM if present and valid; otherwise
    reconstructs from the structured fields.
    """
    body = note.get("body_markdown", "")
    if body:
        return body

    # Fallback: reconstruct from structured fields
    lines: List[str] = []
    lines.append(f"# Weekly Review Pulse — {product} — {week_id}")
    lines.append("")

    # Top themes
    lines.append("## Top Themes")
    for t in note.get("top_themes", []):
        lines.append(f"- **{t.get('name', '')}**: {t.get('summary', '')}")
    lines.append("")

    # Quotes
    lines.append("## What Users Are Saying")
    theme_names = {t.get("id", ""): t.get("name", "") for t in note.get("top_themes", [])}
    for q in note.get("quotes", []):
        tid = q.get("theme_id", "")
        tname = theme_names.get(tid, tid)
        lines.append(f"> {q.get('text', '')}")
        lines.append(f"— {tname} (source: {q.get('source_review_id', '')})")
    lines.append("")

    # Actions
    lines.append("## Recommended Actions")
    for i, a in enumerate(note.get("action_ideas", []), 1):
        tid = a.get("theme_id", "")
        tname = theme_names.get(tid, tid)
        lines.append(f"{i}. **{tname}**: {a.get('text', '')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_note_generation(manifest: RunManifest, paths: RunPaths) -> Dict[str, Any]:
    """Execute Phase 3 note generation.

    Returns a dict with ``status`` and detailed metrics.  All artefacts are
    written to ``paths``.
    """
    paths.ensure_run_dir()
    run_state = RunState(paths.run_state_json, manifest.week_id)
    run_state.mark_phase("note_gen", "in_progress", current_phase="note_gen")

    report: Dict[str, Any] = {
        "status": "failed",
        "week_id": manifest.week_id,
        "product": manifest.product,
        "generated_at": _utc_now(),
        "prompt_version": "weekly_note_v1",
        "word_count": 0,
        "retries": 0,
        "pii_scan_result": [],
        "validation_issues": [],
        "errors": [],
    }

    try:
        # ------------------------------------------------------------------
        # 1. Load Phase 2 artefacts
        # ------------------------------------------------------------------
        theming_report = load_theming_report(paths.theming_report_json)
        themed_reviews = load_themed_reviews(paths.themed_reviews_json)
        legend_themes = load_theme_legend_json(paths.theme_legend_json)

        if not theming_report.get("analytics", {}).get("themes"):
            raise RuntimeError("No theme analytics in theming report — run Phase 2 first")

        logger.info(
            "Loaded theming data: %d themed reviews, %d legend themes",
            len(themed_reviews), len(legend_themes),
        )

        # ------------------------------------------------------------------
        # 2. Select top 3 themes
        # ------------------------------------------------------------------
        top_themes = select_top_themes(theming_report, n=3)
        top_theme_ids = [t["id"] for t in top_themes]

        excluded_themes = []
        all_theme_ids = list(theming_report.get("analytics", {}).get("themes", {}).keys())
        for tid in all_theme_ids:
            if tid not in top_theme_ids:
                tinfo = theming_report["analytics"]["themes"][tid]
                excluded_themes.append({
                    "id": tid,
                    "name": tinfo.get("name", tid),
                    "theme_score": tinfo.get("theme_score", 0),
                    "reason": "Not in top 3 by score",
                })

        logger.info(
            "Top 3 themes: %s (excluded: %s)",
            [t["name"] for t in top_themes],
            [e["name"] for e in excluded_themes],
        )

        # ------------------------------------------------------------------
        # 3. Select quote candidates
        # ------------------------------------------------------------------
        quote_candidates = select_quote_candidates(
            theming_report, themed_reviews, top_theme_ids,
        )
        total_quotes = sum(len(v) for v in quote_candidates.values())
        logger.info("Selected %d quote candidates across %d themes", total_quotes, len(top_theme_ids))

        # ------------------------------------------------------------------
        # 4. Build LLM payload & generate note
        # ------------------------------------------------------------------
        prompt_path = Path(__file__).resolve().parent.parent.parent / "prompts" / "weekly_note_v1.txt"
        system_prompt = prompt_path.read_text(encoding="utf-8")

        payload = build_note_payload(top_themes, quote_candidates, manifest.product, manifest.week_id)

        model = manifest.llm.effective_summary_model if manifest.llm else "llama-3.3-70b-versatile"
        temperature = manifest.llm.temperature_summary if manifest.llm else 0.4

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        logger.info("Generating note with model=%s, temperature=%.1f", model, temperature)

        note_data: Dict[str, Any] = {}
        call_meta: Dict[str, Any] = {}
        retries = 0

        for attempt in range(MAX_RETRIES + 1):
            # If retrying, add shorten instruction
            if attempt > 0:
                payload["shorten_instruction"] = (
                    f"The previous note was over the {MAX_WORDS}-word limit. "
                    "Rewrite more concisely. Remove filler phrases. "
                    "Keep all 3 themes, 3 quotes, and 3 actions but use fewer words."
                )
                retries = attempt

            note_data, call_meta = call_groq_note(
                client,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                user_payload=payload,
            )

            # Check word count
            body = note_data.get("body_markdown", "")
            wc = count_words(body)
            report["word_count"] = wc

            if wc <= MAX_WORDS:
                logger.info("Note generated: %d words (attempt %d)", wc, attempt + 1)
                break
            else:
                logger.warning(
                    "Note over word limit: %d words (attempt %d/%d), retrying",
                    wc, attempt + 1, MAX_RETRIES + 1,
                )

        report["retries"] = retries
        report["call_metadata"] = call_meta

        # ------------------------------------------------------------------
        # 5. Validate note
        # ------------------------------------------------------------------
        validation_issues = validate_note(note_data, themed_reviews)
        quote_issues = validate_quotes_against_source(note_data.get("quotes", []), themed_reviews)
        validation_issues.extend(quote_issues)
        report["validation_issues"] = validation_issues

        # PII scan on final body
        body_md = note_data.get("body_markdown", "")
        pii_result = scan_for_pii(body_md)
        report["pii_scan_result"] = pii_result

        if pii_result:
            logger.warning("PII detected in final note: %s", pii_result)
            # Redact PII from body
            from src.common.pii import redact_text
            body_md, _ = redact_text(body_md)
            note_data["body_markdown"] = body_md

        if validation_issues:
            logger.warning("Note validation issues: %s", validation_issues)

        # ------------------------------------------------------------------
        # 6. Enrich structured note with metadata
        # ------------------------------------------------------------------
        note_data["week_id"] = manifest.week_id
        note_data["product"] = manifest.product
        note_data["word_count"] = count_words(body_md)

        # ------------------------------------------------------------------
        # 7. Render & write artefacts
        # ------------------------------------------------------------------
        # Ensure body_markdown is set
        if not note_data.get("body_markdown"):
            note_data["body_markdown"] = render_note_markdown(note_data, manifest.product, manifest.week_id)

        # weekly_note.json
        with paths.weekly_note_json.open("w", encoding="utf-8") as f:
            json.dump(note_data, f, indent=2, ensure_ascii=False)

        # weekly_note.md
        md_content = note_data.get("body_markdown", "")
        with paths.weekly_note_md.open("w", encoding="utf-8") as f:
            f.write(md_content)
            f.write("\n")

        # note_report.json
        report["status"] = "success"
        report["excluded_themes"] = excluded_themes
        report["top_themes"] = [
            {"id": t["id"], "name": t["name"], "theme_score": t["theme_score"]}
            for t in top_themes
        ]
        report["word_count"] = count_words(md_content)
        with paths.note_report_json.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Update run state
        run_state.mark_phase("note_gen", "complete", current_phase="docs_mcp")
        logger.info("Phase 3 complete: %d words, %d retries", report["word_count"], retries)

        return report

    except Exception as exc:
        logger.exception("Note generation failed: %s", exc)
        report["errors"].append(str(exc))
        run_state.mark_phase("note_gen", "failed", current_phase="note_gen")
        # Write partial report
        with paths.note_report_json.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        raise
