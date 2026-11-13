"""The shape of a finished book record, and the step that turns a raw record into one."""

import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class Book(BaseModel):
    """A finished, validated book record. Every field is required except description."""

    model_config = ConfigDict(extra="forbid", strict=True)

    title: str = Field(min_length=1)
    product_url: str  # canonical URL: the record's identity
    price_text: str = Field(min_length=1)  # raw value, exactly as on the page
    price_gbp: float = Field(ge=0, allow_inf_nan=False)  # clean value, sortable
    availability_text: str = Field(min_length=1)
    rating_text: Literal["One", "Two", "Three", "Four", "Five"]
    description: Optional[str] = Field(default=None, min_length=1)  # some books have none
    source_page: str  # provenance: where the fact came from
    fetched_at: str  # provenance: when it came from there (ISO 8601)

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("must start with https://")
        return value

    @field_validator("fetched_at")
    @classmethod
    def must_be_iso_datetime(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as err:
            raise ValueError("must be an ISO 8601 datetime") from err
        return value


def parse_price_gbp(price_text: str | None) -> float | None:
    """"£51.77" -> 51.77. Returns None when no price can be read, so validation
    fails loudly instead of quietly storing a wrong number."""
    if not isinstance(price_text, str):
        return None
    match = re.search(r"\d+(?:\.\d+)?", price_text.replace(",", ""))
    return float(match.group()) if match else None


def normalize(raw: dict) -> dict:
    """Raw record -> normalized record. The raw price_text is kept next to price_gbp."""
    return {**raw, "price_gbp": parse_price_gbp(raw.get("price_text"))}


def validate_record(raw: dict) -> tuple[dict | None, str | None]:
    """Normalize and validate. Returns (record, None) if good, (None, reason) if not."""
    try:
        book = Book.model_validate(normalize(raw))
    except ValidationError as err:
        reason = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or '(record)'}: {e['msg']}"
            for e in err.errors()
        )
        return None, reason
    return book.model_dump(), None
