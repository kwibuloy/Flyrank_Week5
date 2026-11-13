"""Entry point for the Books to Scrape scraper.

Target and scope are documented in ../README.md ("Target classification").
"""

import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
MAX_PAGES = 3

# An honest user-agent: a site owner reading their logs can find out who we are.
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/kwibuloy/Flyrank_Week5)"
# Give up on a request after this many seconds; never wait forever.
TIMEOUT_S = 5
# Minimum gap between real requests to the site. Cache hits skip it.
REQUEST_DELAY_S = 0.5

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

_last_request_at = 0.0


def cache_name_for(url: str) -> str:
    """https://books.toscrape.com/catalogue/page-1.html -> catalogue-page-1.html"""
    path = urlparse(url).path.lstrip("/")
    return path.replace("/", "-") or "index.html"


def polite_delay() -> None:
    """Wait until at least REQUEST_DELAY_S has passed since the previous real request."""
    global _last_request_at
    wait = _last_request_at + REQUEST_DELAY_S - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def get_page(url: str) -> str:
    """Fetch a URL once and keep the HTML in cache/; later runs read the saved copy."""
    cache_name = cache_name_for(url)
    cache_file = CACHE_DIR / cache_name

    # Bytes in, bytes out: the cache holds exactly what the server sent.
    if cache_file.exists():
        body = cache_file.read_bytes()
        print(f"CACHE HIT  {cache_name} ({len(body)} bytes)")
        return body.decode("utf-8")

    polite_delay()
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)

    # Only 200 means "here is your page". Anything else is a failed fetch.
    if response.status_code != 200:
        raise RuntimeError(f"Failed fetch: {url} returned HTTP {response.status_code}")

    body = response.content
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(body)
    print(f"FETCH      {url} ({len(body)} bytes)")
    return body.decode("utf-8")


def parse_catalogue(html: str, page_url: str) -> tuple[list[str], str | None]:
    """Return the absolute book links on one catalogue page, and its "next" link (if any)."""
    soup = BeautifulSoup(html, "html.parser")
    book_urls = [
        urljoin(page_url, a["href"]) for a in soup.select("article.product_pod h3 a[href]")
    ]
    next_link = soup.select_one("li.next a[href]")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return book_urls, next_url


def discover_books() -> list[str]:
    """Follow the catalogue's own "next" links, stopping after MAX_PAGES pages."""
    discovered: list[str] = []
    page_url: str | None = START_URL
    pages = 0

    while page_url and pages < MAX_PAGES:
        book_urls, page_url_next = parse_catalogue(get_page(page_url), page_url)
        discovered.extend(book_urls)
        pages += 1
        page_url = page_url_next

    unique = list(dict.fromkeys(discovered))  # drops duplicates, keeps order
    print(f"catalogue_pages={pages}, discovered={len(discovered)}, unique_urls={len(unique)}")
    return unique


def main() -> None:
    print(f"Target: {BASE_URL} (first {MAX_PAGES} catalogue pages only)")
    discover_books()


if __name__ == "__main__":
    try:
        main()
    except requests.Timeout:
        sys.exit(f"Request timed out after {TIMEOUT_S} s")
    except (requests.RequestException, RuntimeError) as err:
        sys.exit(str(err))
