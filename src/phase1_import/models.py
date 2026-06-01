from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawReview:
    store: str
    review_id: str | None
    rating: int
    title: str
    text: str
    review_date: date


@dataclass
class NormalizedReview:
    review_id: str
    store: str
    rating: int
    title: str
    text: str
    review_date: date
    language: str = ""
    char_count: int = 0

    def to_csv_row(self) -> dict[str, str | int]:
        return {
            "review_id": self.review_id,
            "store": self.store,
            "rating": self.rating,
            "title": self.title,
            "text": self.text,
            "review_date": self.review_date.isoformat(),
            "language": self.language,
            "char_count": self.char_count,
        }


CANONICAL_CSV_COLUMNS = [
    "review_id",
    "store",
    "rating",
    "title",
    "text",
    "review_date",
    "language",
    "char_count",
]
