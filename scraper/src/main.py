"""Entry point for the Books to Scrape scraper.

Target and scope are documented in ../README.md ("Target classification").

Usage:
    python src/main.py                    normal run
    python src/main.py --with-broken-url  same run plus one made-up book URL,
                                          to prove failures are survived
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from fetcher import get_page, stats
from parse import parse_book, parse_catalogue
from schema import validate_record

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
MAX_PAGES = 3

# A book page that does not exist. Only added with --with-broken-url.
# It costs the site one 404 request per demo run, and a 404 is never retried.
BROKEN_URL = urljoin(BASE_URL, "catalogue/this-book-does-not-exist_0/index.html")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def iso(dt: datetime) -> str:
    """UTC datetime -> '2026-11-13T14:00:25.038Z'."""
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def discover_books(failures: list[dict]) -> dict:
    """Follow the catalogue's own "next" links, stopping after MAX_PAGES pages."""
    found: dict[str, str] = {}  # product_url -> source_page (first sighting wins)
    discovered = 0
    page_url: str | None = START_URL
    pages = 0

    while page_url and pages < MAX_PAGES:
        try:
            book_urls, next_url = parse_catalogue(get_page(page_url).html, page_url)
        except Exception as err:  # noqa: BLE001 - one bad page must not crash the run
            # Without this page we cannot see its "next" link, so discovery stops here.
            print(f"FAILED     {page_url}: {err}", file=sys.stderr)
            failures.append({"url": page_url, "stage": "catalogue", "reason": str(err)})
            break
        discovered += len(book_urls)
        for url in book_urls:
            found.setdefault(url, page_url)
        pages += 1
        page_url = next_url

    print(f"catalogue_pages={pages}, discovered={discovered}, unique_urls={len(found)}")
    return {"pages": pages, "discovered": discovered, "books": list(found.items())}


def extract_books(books: list[tuple[str, str]], failures: list[dict]) -> list[dict]:
    """Fetch and parse every book detail page. Each page is handled on its own:
    one broken page is logged and skipped, and the rest carry on."""
    records = []
    for product_url, source_page in books:
        try:
            page = get_page(product_url)
            records.append(
                parse_book(
                    page.html,
                    product_url=product_url,
                    source_page=source_page,
                    fetched_at=page.fetched_at,
                )
            )
        except Exception as err:  # noqa: BLE001 - one bad page must not crash the run
            print(f"FAILED     {product_url}: {err}", file=sys.stderr)
            failures.append({"url": product_url, "stage": "detail", "reason": str(err)})
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
    parser = argparse.ArgumentParser(description="Scrape the first 3 pages of Books to Scrape.")
    parser.add_argument(
        "--with-broken-url",
        action="store_true",
        help="add one made-up book URL on purpose, to prove a broken page is skipped",
    )
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    failures: list[dict] = []

    print(f"Target: {BASE_URL} (first {MAX_PAGES} catalogue pages only)")
    discovery = discover_books(failures)
    books = list(discovery["books"])
    if args.with_broken_url:
        print(f"Injecting one made-up URL on purpose: {BROKEN_URL}")
        books.append((BROKEN_URL, "injected by --with-broken-url"))

    raw_records = extract_books(books, failures)
    good, errors = validate_all(raw_records)

    # Each run rewrites the files from this run's records, so re-running gives
    # the same 60 records, never an ever-growing pile (idempotency).
    write_json("books.json", good)
    write_json("errors.json", errors)

    finished_at = datetime.now(timezone.utc)
    report = {
        "started_at": iso(started_at),
        "finished_at": iso(finished_at),
        "duration_ms": round((finished_at - started_at).total_seconds() * 1000),
        "target": BASE_URL,
        "injected_broken_url": args.with_broken_url,
        "catalogue_pages": discovery["pages"],
        "discovered_urls": discovery["discovered"],
        "unique_urls": len(discovery["books"]),
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "retries": stats["retries"],
        "valid_records": len(good),
        "invalid_records": len(errors),
        "failed_pages": len(failures),
        "failures": failures,
    }
    write_json("run-report.json", report)

    print(
        f"valid_records={report['valid_records']}, invalid_records={report['invalid_records']}, "
        f"failed_pages={report['failed_pages']}, pages_fetched={report['pages_fetched']}, "
        f"cache_hits={report['cache_hits']}, duration_ms={report['duration_ms']}"
    )


if __name__ == "__main__":
    # Windows consoles may not be UTF-8; make sure "£" prints instead of crashing.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except Exception as err:  # noqa: BLE001
        sys.exit(f"Run aborted: {err}")
