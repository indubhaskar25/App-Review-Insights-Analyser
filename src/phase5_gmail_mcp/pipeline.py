"""Phase 5 – Gmail Draft via MCP pipeline"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
import urllib.request

from src.common.manifest import RunManifest
from src.common.run_paths import RunPaths
from src.common.run_state import RunState, load_run_state

logger = logging.getLogger("app_review.phase5")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_gmail_mcp(manifest: RunManifest, paths: RunPaths) -> dict:
    """
    Create a Gmail draft using the MCP server.
    """
    logger.info("Starting Phase 5: Gmail MCP")
    run_state_dict = load_run_state(paths.run_state_json)
    if run_state_dict.get("phases", {}).get("note_gen", {}).get("status") != "complete":
        raise RuntimeError("Phase 3 (note_gen) is not complete. Cannot run Phase 5.")

    run_state = RunState(paths.run_state_json, manifest.week_id)
    run_state.mark_phase("gmail_mcp", "in_progress")

    report = {
        "status": "in_progress",
        "draft_id": None,
        "created_at": None,
        "errors": []
    }

    try:
        if not manifest.email_to:
            raise ValueError("Email recipient (EMAIL_TO) is not set in environment or manifest.")

        # Read the markdown note
        if not paths.weekly_note_md.exists():
            raise FileNotFoundError(f"Weekly note not found at {paths.weekly_note_md}")
            
        with open(paths.weekly_note_md, "r", encoding="utf-8") as f:
            note_content = f.read()

        # Try to read doc_url from Phase 4
        doc_url = ""
        if paths.publish_result_json.exists():
            with open(paths.publish_result_json, "r", encoding="utf-8") as f:
                publish_data = json.load(f)
                doc_url = publish_data.get("doc_url", "")

        server_url = (manifest.mcp.server_url if manifest.mcp else "") or "https://mcp-server-production-4969.up.railway.app"
        endpoint = f"{server_url.rstrip('/')}/create_email_draft"
        logger.info(f"Sending request to MCP server: {endpoint}")

        subject = manifest.email_subject_template.format(product=manifest.product, week_id=manifest.week_id)
        
        body = (
            f"Here is the weekly review pulse for {manifest.product}.\n\n"
            f"{note_content}\n\n"
        )
        if doc_url:
            body += f"Full doc: {doc_url}\n\n"
            
        body += "Draft — review before sending"

        # Prepare payload
        payload = {
            "to": manifest.email_to,
            "subject": subject,
            "body": body
        }
        
        # Send HTTP POST
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint, 
            data=data, 
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode("utf-8")
            resp_data = json.loads(resp_body)
            
        if resp_data.get("status") == "error":
            raise RuntimeError(f"MCP server returned error: {resp_data.get('message')} - {resp_data.get('details')}")

        draft_id = resp_data.get("draft_id", "unknown_id")
        logger.info(f"Successfully created Gmail draft (ID: {draft_id})")

        # email_draft_result.json
        email_result = {
            "status": "success",
            "draft_id": draft_id,
            "to": manifest.email_to,
            "subject": subject,
            "created_at": _utc_now()
        }
        with paths.email_draft_result_json.open("w", encoding="utf-8") as f:
            json.dump(email_result, f, indent=2)

        # gmail_report.json
        report["status"] = "success"
        report["created_at"] = email_result["created_at"]
        report["draft_id"] = draft_id
        
        with paths.gmail_report_json.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        run_state.mark_phase("gmail_mcp", "complete", current_phase="complete")
        return report

    except Exception as exc:
        logger.exception("Gmail MCP failed: %s", exc)
        report["status"] = "failed"
        report["errors"].append(str(exc))
        run_state.mark_phase("gmail_mcp", "failed", current_phase="gmail_mcp")
        with paths.gmail_report_json.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        raise
