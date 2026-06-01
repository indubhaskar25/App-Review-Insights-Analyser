"""Phase 5: Gmail draft via MCP."""

from src.phase4_docs_mcp.pipeline import (
    call_mcp_create_email_draft,
    create_gmail_draft,
)

__all__ = [
    "call_mcp_create_email_draft",
    "create_gmail_draft",
]
