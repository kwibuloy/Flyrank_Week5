"""Entry point for the Books to Scrape scraper.

Target and scope are documented in ../README.md ("Target classification").
"""

import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

from fetcher import TIMEOUT_S, get_page
from parse import parse_book, parse_catalogue
from schema import validate_record

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
MAX_PAGES = 3

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def discover_books() -> list[tuple[str, str]]:
    """Follow the catalogue's own "next" links, stopping after MAX_PAGES pages.

    Returns (product_url, source_page) for each unique book.
    """
    found: dict[str, str] = {}  # product_url -> source_page (first sighting wins)
    discovered = 0
    page_url: str | None = START_URL
    pages = 0

    while page_url and pages < MAX_PAGES:
        book_urls, next_url = parse_catalogue(get_page(page_url).html, page_url)
        discovered += len(book_urls)
        for url in book_urls:
            found.setdefault(url, page_url)
        pages += 1
        page_url = next_url

    print(f"catalogue_pages={pages}, discovered={discovered}, unique_urls={len(found)}")
    return list(found.items())


def extract_books(books: list[tuple[str, str]]) -> list[dict]:
    """Fetch and parse every book detail page into a raw record."""
    records = []
    for product_url, source_page in books:
        page = get_page(product_url)
        records.append(
            parse_book(
                page.html,
                product_url=product_url,
                source_page=source_page,
                fetched_at=page.fetched_at,
            )
        )
    print(f"detail_pages={len(records)}")
    return records


def validate_all(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validate every record before storing it. Good records are keyed by their
    canonical product_url, so the same book can only ever count once."""
    good: dict[str, dict] = {}
    errors: list[dict] = []
    for raw in raw_records:
        record, reason = validate_record(raw)
        if record is not None:
            good[record["product_url"]] = record
        else:
            errors.append({"product_url": raw.get("product_url"), "reason": reason, "raw": raw})
    return list(good.values()), errors


def write_json(file_name: str, data) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    (OUTPUT_DIR / file_name).write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    print(f"Target: {BASE_URL} (first {MAX_PAGES} catalogue pages only)")
    raw_records = extract_books(discover_books())
    books, errors = validate_all(raw_records)

    # Each run rewrites the files from this run's records, so re-running gives
    # the same 60 records, never an ever-growing pile (idempotency).
    write_json("books.json", books)
    write_json("errors.json", errors)
    print(f"valid_records={len(books)}, invalid_records={len(errors)}")


if __name__ == "__main__":
    # Windows consoles may not be UTF-8; make sure "£" prints instead of crashing.
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except requests.Timeout:
        sys.exit(f"Request timed out after {TIMEOUT_S} s")
    except (requests.RequestException, RuntimeError) as err:
        sys.exit(str(err))
