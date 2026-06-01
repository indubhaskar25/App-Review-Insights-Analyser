from __future__ import annotations

from pathlib import Path

from src.phase1_import.adapters.base import (
    StoreAdapter,
    make_content_hash,
    parse_date,
    parse_rating,
    read_csv_rows,
)
from src.phase1_import.models import RawReview

# Normalized header -> list of source column aliases
APP_STORE_COLUMN_MAP = {
    "review_id": ["review_id", "id"],
    "created": ["created", "date", "review_date"],
    "rating": ["rating", "star_rating"],
    "title": ["title"],
    "review": ["review", "body", "content", "review_text"],
}


def _pick(row: dict[str, str], aliases: list[str]) -> str:
    for key in aliases:
        if key in row and row[key]:
            return row[key]
    return ""


class AppStoreAdapter(StoreAdapter):
    store = "app_store"

    def parse_file(self, path: Path) -> list[RawReview]:
        if not path.exists():
            return []

        _, rows = read_csv_rows(path)
        if not rows:
            return []
        reviews: list[RawReview] = []

        for row in rows:
            text = _pick(row, APP_STORE_COLUMN_MAP["review"])
            rating = parse_rating(_pick(row, APP_STORE_COLUMN_MAP["rating"]))
            review_date = parse_date(_pick(row, APP_STORE_COLUMN_MAP["created"]))
            if rating is None or review_date is None:
                continue

            native_id = _pick(row, APP_STORE_COLUMN_MAP["review_id"]) or None
            title = _pick(row, APP_STORE_COLUMN_MAP["title"])

            reviews.append(
                RawReview(
                    store=self.store,
                    review_id=native_id,
                    rating=rating,
                    title=title,
                    text=text,
                    review_date=review_date,
                )
            )

        return reviews
