"""Polite HTTP fetching with an on-disk cache.

Every real request: identifying user-agent, timeout, status check, delay.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

# An honest user-agent: a site owner reading their logs can find out who we are.
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/kwibuloy/Flyrank_Week5)"
# Give up on a request after this many seconds; never wait forever.
TIMEOUT_S = 5
# Minimum gap between real requests to the site. Cache hits skip it.
REQUEST_DELAY_S = 0.5

# After a timeout or 5xx, wait this long and try exactly once more.
RETRY_DELAY_S = 2

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last_request_at = 0.0

# Counters for the run report.
stats = {"pages_fetched": 0, "cache_hits": 0, "retries": 0}


class FetchError(Exception):
    """A failed fetch that remembers its HTTP status (None if there was no response)."""

    def __init__(self, message: str, status: int | None = None, timed_out: bool = False):
        super().__init__(message)
        self.status = status
        self.timed_out = timed_out


def is_retryable(err: FetchError) -> bool:
    """Only a timeout or a server error (5xx) is worth one more try.
    404 = the page does not exist; 403 = the site said no. Never retry those."""
    return err.timed_out or (err.status is not None and err.status >= 500)


@dataclass
class Page:
    html: str
    fetched_at: str  # when the HTML actually left the site: provenance
    from_cache: bool


def iso_utc(ts: float) -> str:
    """Unix timestamp -> '2026-11-13T14:00:25.038Z'."""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


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


def get_page(url: str) -> Page:
    """Fetch a URL once and keep the HTML in cache/; later runs read the saved copy.

    On a cache hit, fetched_at is the cache file's write time - the moment the
    HTML was really downloaded, not the moment we re-read it.
    """
    cache_name = cache_name_for(url)
    cache_file = CACHE_DIR / cache_name

    # Bytes in, bytes out: the cache holds exactly what the server sent.
    if cache_file.exists():
        body = cache_file.read_bytes()
        stats["cache_hits"] += 1
        print(f"CACHE HIT  {cache_name} ({len(body)} bytes)")
        return Page(body.decode("utf-8"), iso_utc(cache_file.stat().st_mtime), True)

    try:
        body = fetch_once(url)
    except FetchError as err:
        if not is_retryable(err):
            raise
        stats["retries"] += 1
        print(f"RETRY      {url} after {err}")
        time.sleep(RETRY_DELAY_S)
        body = fetch_once(url)

    fetched_at = iso_utc(time.time())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(body)
    print(f"FETCH      {url} ({len(body)} bytes)")
    return Page(body.decode("utf-8"), fetched_at, False)


def fetch_once(url: str) -> bytes:
    """One real request to the site."""
    polite_delay()
    stats["pages_fetched"] += 1
    try:
        response = _session.get(url, timeout=TIMEOUT_S)
    except requests.Timeout as err:
        raise FetchError(f"timed out after {TIMEOUT_S} s", timed_out=True) from err
    except requests.RequestException as err:
        raise FetchError(f"network error: {err.__class__.__name__}") from err

    # Only 200 means "here is your page". Anything else is a failed fetch.
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code}", status=response.status_code)
    return response.content
