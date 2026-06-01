"""Phase 4 pipeline: Publish weekly note to Google Docs via MCP."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.common import run_state
from src.common.logging_config import setup_run_logger
from src.common.manifest import MCPConfig, RunManifest
from src.common.run_paths import RunPaths

MCP_SERVER_URL = "https://mcp-server-production-4969.up.railway.app"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MCP Client
# ---------------------------------------------------------------------------

def call_mcp_append_doc(
    server_url: str,
    doc_id: str,
    content: str,
    max_retries: int = 2,
    retry_delay: int = 5,
) -> dict[str, Any]:
    """Append content to a Google Doc via the MCP server's REST endpoint.

    Args:
        server_url: MCP server base URL.
        doc_id: Google Docs file ID (the long alphanumeric ID from the URL).
        content: Markdown/text content to append.
        max_retries: Number of retries on failure.
        retry_delay: Delay between retries in seconds.

    Returns:
        Response JSON from the MCP server.
    """
    url = f"{server_url.rstrip('/')}/append_to_doc"
    payload = {"doc_id": doc_id, "content": content}
    logger.info("Calling MCP server to append content to Google Doc: %s", url)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info("Retrying MCP call (attempt %d/%d) …", attempt, max_retries)
                time.sleep(retry_delay)

            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            logger.info("MCP append_to_doc succeeded on attempt %d", attempt)
            return {"success": True, "result": result, "attempts": attempt + 1}
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning("MCP call failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)
        except Exception as exc:
            last_error = str(exc)
            logger.error("Unexpected error during MCP call (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)

    return {"success": False, "error": last_error, "attempts": max_retries + 1}


def call_mcp_create_email_draft(
    server_url: str,
    to: str,
    subject: str,
    body: str,
    max_retries: int = 2,
    retry_delay: int = 5,
) -> dict[str, Any]:
    """Create a Gmail draft via the MCP server's REST endpoint.

    Args:
        server_url: MCP server base URL.
        to: Recipient email address.
        subject: Email subject line.
        body: Email body content.
        max_retries: Number of retries on failure.
        retry_delay: Delay between retries in seconds.

    Returns:
        Response JSON from the MCP server.
    """
    url = f"{server_url.rstrip('/')}/create_email_draft"
    payload = {"to": to, "subject": subject, "body": body}
    logger.info("Calling MCP server to create Gmail draft for: %s", to)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info("Retrying MCP email call (attempt %d/%d) …", attempt, max_retries)
                time.sleep(retry_delay)

            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            logger.info("MCP create_email_draft succeeded on attempt %d", attempt)
            return {"success": True, "result": result, "attempts": attempt + 1}
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning("MCP email call failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)
        except Exception as exc:
            last_error = str(exc)
            logger.error("Unexpected error during MCP email call (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)

    return {"success": False, "error": last_error, "attempts": max_retries + 1}


# ---------------------------------------------------------------------------
# Phase 4 Orchestrator
# ---------------------------------------------------------------------------

def publish_to_google_docs(manifest: RunManifest, paths: RunPaths) -> None:
    """Publish the weekly note to Google Docs via the MCP server.

    Flow:
        1. Load Phase 3 output (weekly_note.md).
        2. Append to the configured Google Doc via MCP server.
        3. Write publish_result.json and docs_report.json.
        4. Update run_state.
    """
    setup_run_logger(paths)
    run_state.mark_started(paths.run_state_json, "docs_publish")

    # --- Load weekly note ---
    if not paths.weekly_note_md.exists():
        msg = "Phase 3 output not found: weekly_note.md"
        logger.error(msg)
        run_state.mark_failed(paths.run_state_json, "docs_publish", msg)
        raise FileNotFoundError(msg)

    note_content = paths.weekly_note_md.read_text(encoding="utf-8")
    logger.info("Loaded weekly note from %s (%d chars)", paths.weekly_note_md, len(note_content))

    # --- Load MCP config ---
    mcp_cfg = manifest.mcp or MCPConfig.from_env()
    if not mcp_cfg.server_url:
        msg = "MCP_SERVER_URL not configured in environment or manifest"
        logger.error(msg)
        run_state.mark_failed(paths.run_state_json, "docs_publish", msg)
        raise ValueError(msg)
    if not mcp_cfg.google_doc_id:
        msg = "GOOGLE_DOC_ID not configured in environment or manifest"
        logger.error(msg)
        run_state.mark_failed(paths.run_state_json, "docs_publish", msg)
        raise ValueError(msg)

    # Extract just the file ID from the full URL if needed
    doc_id = mcp_cfg.google_doc_id
    # Handle full Google Docs URLs like: https://docs.google.com/document/d/DOC_ID/edit
    if "docs.google.com" in doc_id:
        import re
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', doc_id)
        if match:
            doc_id = match.group(1)
            logger.info("Extracted Google Doc ID from URL: %s", doc_id)

    # --- Build header ---
    header = (
        f"\n\n{'='*60}\n"
        f"# {manifest.product} — Weekly Review Pulse: {manifest.week_id}\n"
        f"Published: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"{'='*60}\n\n"
    )
    full_content = header + note_content

    # --- Call MCP server ---
    result = call_mcp_append_doc(mcp_cfg.server_url, doc_id, full_content)

    # --- Build report ---
    report: dict[str, Any] = {
        "phase": "docs_publish",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "week_id": manifest.week_id,
        "product": manifest.product,
        "mcp_server": mcp_cfg.server_url,
        "google_doc_id": doc_id,
        "note_source": str(paths.weekly_note_md),
        "chars_appended": len(full_content),
        "mcp_result": result,
    }

    paths.docs_report_json.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote docs report to %s", paths.docs_report_json)

    if not result.get("success"):
        msg = f"MCP publish failed: {result.get('error', 'unknown error')}"
        logger.error(msg)
        run_state.mark_failed(paths.run_state_json, "docs_publish", msg)
        raise RuntimeError(msg)

    paths.publish_result_json.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote publish result to %s", paths.publish_result_json)
    run_state.mark_completed(paths.run_state_json, "docs_publish")


# ---------------------------------------------------------------------------
# Phase 5 Orchestrator
# ---------------------------------------------------------------------------

def create_gmail_draft(manifest: RunManifest, paths: RunPaths) -> None:
    """Create a Gmail draft with the weekly note via the MCP server.

    Flow:
        1. Load Phase 3 output (weekly_note.md).
        2. Format as email with subject from manifest.
        3. Create Gmail draft via MCP server.
        4. Write email_draft_result.json and gmail_report.json.
        5. Update run_state.
    """
    setup_run_logger(paths)
    run_state.mark_started(paths.run_state_json, "gmail_draft")

    # --- Load weekly note ---
    if not paths.weekly_note_md.exists():
        msg = "Phase 3 output not found: weekly_note.md"
        logger.error(msg)
        run_state.mark_failed(paths.run_state_json, "gmail_draft", msg)
        raise FileNotFoundError(msg)

    note_content = paths.weekly_note_md.read_text(encoding="utf-8")
    logger.info("Loaded weekly note from %s (%d chars)", paths.weekly_note_md, len(note_content))

    # --- Load MCP config ---
    mcp_cfg = manifest.mcp or MCPConfig.from_env()
    if not mcp_cfg.server_url:
        msg = "MCP_SERVER_URL not configured in environment or manifest"
        logger.error(msg)
        run_state.mark_failed(paths.run_state_json, "gmail_draft", msg)
        raise ValueError(msg)

    # --- Build email ---
    subject = manifest.email_subject_template.format(
        product=manifest.product,
        week_id=manifest.week_id,
    )
    logger.info("Email subject: %s", subject)
    logger.info("Email recipient: %s", manifest.email_to)

    # --- Call MCP server ---
    result = call_mcp_create_email_draft(
        mcp_cfg.server_url,
        to=manifest.email_to,
        subject=subject,
        body=note_content,
    )

    # --- Build report ---
    report: dict[str, Any] = {
        "phase": "gmail_draft",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "week_id": manifest.week_id,
        "product": manifest.product,
        "mcp_server": mcp_cfg.server_url,
        "email_to": manifest.email_to,
        "email_subject": subject,
        "note_source": str(paths.weekly_note_md),
        "body_chars": len(note_content),
        "mcp_result": result,
    }

    paths.gmail_report_json.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote Gmail report to %s", paths.gmail_report_json)

    if not result.get("success"):
        msg = f"MCP email draft failed: {result.get('error', 'unknown error')}"
        logger.error(msg)
        run_state.mark_failed(paths.run_state_json, "gmail_draft", msg)
        raise RuntimeError(msg)

    paths.email_draft_result_json.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote email draft result to %s", paths.email_draft_result_json)
    run_state.mark_completed(paths.run_state_json, "gmail_draft")


# ---------------------------------------------------------------------------
# Full pipeline (Phases 4 + 5 combined)
# ---------------------------------------------------------------------------

def run_mcp_pipeline(manifest: RunManifest, paths: RunPaths) -> None:
    """Run both Phase 4 (Docs publish) and Phase 5 (Gmail draft).

    This is the convenience function for the GitHub Actions workflow.
    """
    # Phase 4: Publish to Google Docs
    logger.info("=== Phase 4: Publishing to Google Docs ===")
    publish_to_google_docs(manifest, paths)

    # Phase 5: Create Gmail draft
    logger.info("=== Phase 5: Creating Gmail draft ===")
    create_gmail_draft(manifest, paths)

    logger.info("MCP pipeline complete: Docs + Email")
