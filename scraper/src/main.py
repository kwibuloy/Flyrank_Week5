"""Entry point for the Books to Scrape scraper.

Target and scope are documented in ../README.md ("Target classification").
"""

import sys
from pathlib import Path

import requests

BASE_URL = "https://books.toscrape.com/"
MAX_PAGES = 3

# An honest user-agent: a site owner reading their logs can find out who we are.
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/kwibuloy/Flyrank_Week5)"
# Give up on a request after this many seconds; never wait forever.
TIMEOUT_S = 5

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def get_page(url: str, cache_name: str) -> str:
    """Fetch a URL once and keep the HTML in cache/; later runs read the saved copy."""
    cache_file = CACHE_DIR / cache_name

    # Bytes in, bytes out: the cache holds exactly what the server sent.
    if cache_file.exists():
        body = cache_file.read_bytes()
        print(f"CACHE HIT  {cache_name} ({len(body)} bytes)")
        return body.decode("utf-8")

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)

    # Only 200 means "here is your page". Anything else is a failed fetch.
    if response.status_code != 200:
        raise RuntimeError(f"Failed fetch: {url} returned HTTP {response.status_code}")

    body = response.content
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(body)
    print(f"FETCH      {url} ({len(body)} bytes)")
    return body.decode("utf-8")


def main() -> None:
    print(f"Target: {BASE_URL} (first {MAX_PAGES} catalogue pages only)")
    get_page(f"{BASE_URL}catalogue/page-1.html", "catalogue-page-1.html")


if __name__ == "__main__":
    try:
        main()
    except requests.Timeout:
        sys.exit(f"Request timed out after {TIMEOUT_S} s")
    except (requests.RequestException, RuntimeError) as err:
        sys.exit(str(err))
