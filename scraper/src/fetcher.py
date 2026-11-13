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

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last_request_at = 0.0


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
        print(f"CACHE HIT  {cache_name} ({len(body)} bytes)")
        return Page(body.decode("utf-8"), iso_utc(cache_file.stat().st_mtime), True)

    polite_delay()
    response = _session.get(url, timeout=TIMEOUT_S)

    # Only 200 means "here is your page". Anything else is a failed fetch.
    if response.status_code != 200:
        raise RuntimeError(f"Failed fetch: {url} returned HTTP {response.status_code}")

    body = response.content
    fetched_at = iso_utc(time.time())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(body)
    print(f"FETCH      {url} ({len(body)} bytes)")
    return Page(body.decode("utf-8"), fetched_at, False)
