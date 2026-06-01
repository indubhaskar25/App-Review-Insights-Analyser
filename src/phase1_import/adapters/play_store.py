from __future__ import annotations

from pathlib import Path

from src.phase1_import.adapters.base import (
    StoreAdapter,
    parse_date,
    parse_rating,
    read_csv_rows,
)
from src.phase1_import.models import RawReview

PLAY_STORE_COLUMN_MAP = {
    "review_id": ["review_id", "review_link"],
    "review_submit_date": [
        "review_submit_date",
        "review_date",
        "submit_date",
        "date",
    ],
    "star_rating": ["star_rating", "rating"],
    "review_text": ["review_text", "review", "text", "body"],
    "review_title": ["review_title", "title"],
}


def _pick(row: dict[str, str], aliases: list[str]) -> str:
    for key in aliases:
        if key in row and row[key]:
            return row[key]
    return ""


class PlayStoreAdapter(StoreAdapter):
    store = "play_store"

    def parse_file(self, path: Path) -> list[RawReview]:
        if not path.exists():
            raise FileNotFoundError(f"Play Store CSV not found: {path}")

        _, rows = read_csv_rows(path)
        reviews: list[RawReview] = []

        for row in rows:
            text = _pick(row, PLAY_STORE_COLUMN_MAP["review_text"])
            rating = parse_rating(_pick(row, PLAY_STORE_COLUMN_MAP["star_rating"]))
            review_date = parse_date(_pick(row, PLAY_STORE_COLUMN_MAP["review_submit_date"]))
            if rating is None or review_date is None:
                continue

            native_id = _pick(row, PLAY_STORE_COLUMN_MAP["review_id"]) or None
            title = _pick(row, PLAY_STORE_COLUMN_MAP["review_title"])

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
