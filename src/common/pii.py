from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL = re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b", re.IGNORECASE)
PHONE = re.compile(r"\b\+?\d{10,13}\b")
HANDLE = re.compile(r"@[\w.]{2,}")
LONG_NUMERIC_ID = re.compile(r"\b\d{12,}\b")

REDACTED = "[REDACTED]"


@dataclass
class RedactionStats:
    emails: int = 0
    phones: int = 0
    handles: int = 0
    long_ids: int = 0

    @property
    def total(self) -> int:
        return self.emails + self.phones + self.handles + self.long_ids

    def to_dict(self) -> dict[str, int]:
        return {
            "emails": self.emails,
            "phones": self.phones,
            "handles": self.handles,
            "long_ids": self.long_ids,
            "total": self.total,
        }

    def merge(self, other: RedactionStats) -> None:
        self.emails += other.emails
        self.phones += other.phones
        self.handles += other.handles
        self.long_ids += other.long_ids


def redact_text(text: str) -> tuple[str, RedactionStats]:
    stats = RedactionStats()
    if not text:
        return text, stats

    result = text
    for pattern, field in (
        (EMAIL, "emails"),
        (PHONE, "phones"),
        (HANDLE, "handles"),
        (LONG_NUMERIC_ID, "long_ids"),
    ):
        updated, count = pattern.subn(REDACTED, result)
        if count:
            setattr(stats, field, getattr(stats, field) + count)
        result = updated

    return result, stats


def scan_for_pii(text: str) -> list[str]:
    """Return list of PII types still present (empty if clean)."""
    found: list[str] = []
    if EMAIL.search(text):
        found.append("email")
    if PHONE.search(text):
        found.append("phone")
    if HANDLE.search(text):
        found.append("handle")
    if LONG_NUMERIC_ID.search(text):
        found.append("long_id")
    return found
