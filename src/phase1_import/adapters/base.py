from __future__ import annotations

import csv
import hashlib
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path

from src.phase1_import.models import RawReview


def normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"No headers found in {path}")
        headers = [normalize_header(h) for h in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {
                normalize_header(k): (v or "").strip()
                for k, v in raw.items()
                if k is not None
            }
            rows.append(row)
        return headers, rows


def parse_rating(value: str) -> int | None:
    if not value:
        return None
    cleaned = value.strip().split(".")[0]
    if not cleaned.isdigit():
        return None
    rating = int(cleaned)
    if 1 <= rating <= 5:
        return rating
    return None


def parse_date(value: str) -> date | None:
    if not value:
        return None
    value = value.strip()
    formats = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            continue
    if "T" in value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")[:19]).date()
        except ValueError:
            pass
    return None


def make_content_hash(store: str, review_date: date, rating: int, text: str) -> str:
    snippet = text[:200].strip().lower()
    payload = f"{store}|{review_date.isoformat()}|{rating}|{snippet}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class StoreAdapter(ABC):
    store: str

    @abstractmethod
    def parse_file(self, path: Path) -> list[RawReview]:
        ...
