# Books to Scrape scraper

A small, polite web scraper built as a FlyRank Week 5 internship exercise. It reads the
first 3 catalogue pages of [Books to Scrape](https://books.toscrape.com/), visits each of
the 60 books, validates every record, and writes clean JSON plus a report of the run.

## Run it

**Lane:** Python **3.10 or newer**, using `requests`, Beautiful Soup and Pydantic. Install
Python from [python.org](https://www.python.org/downloads/) and check it with `python --version`
(on macOS/Linux the command may be `python3`).

Copy-paste this from any folder:

```bash
git clone https://github.com/kwibuloy/Flyrank_Week5.git && cd Flyrank_Week5/scraper && python -m pip install -r requirements.txt && python src/main.py
```

That's it. A fresh clone, install and full run took **52 seconds** in testing. You get:

| File | What it is |
| --- | --- |
| `output/books.json` | the 60 validated book records |
| `output/run-report.json` | counts, failures, cache hits and duration of the run |
| `output/errors.json` | records that failed validation, each with its reason (`[]` when none) |
| `cache/` | the downloaded HTML (git-ignored); later runs read from here |

Prefer an isolated environment? Create a virtualenv first:

```bash
python -m venv .venv
```

Then activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on
macOS/Linux) before the `pip install` step.

Other commands (run from `scraper/`):

```bash
python scripts/check_output.py
```

Checks `books.json`: exactly 60 records, every `price_gbp` a number, every URL `https://`.

```bash
python src/main.py --with-broken-url
```

Same run plus one made-up book URL, to prove a broken page is logged and skipped
(`failed_pages: 1`, still 60 good records). It costs the site a single 404, never retried.

The `output/` files in this repo are a real sample from the fresh-clone run shown below.

## Target classification

**Site:** [Books to Scrape](https://books.toscrape.com/) — part of [toscrape.com](https://toscrape.com/).

**Why this site:** toscrape.com describes itself as a "Web Scraping Sandbox", and lists
Books to Scrape as "a fictional bookstore that desperately wants to be scraped … a safe
place for beginners learning web scraping". It exists so people can practise scraping on
it, and that statement on their page is my permission. A sandbox like this is the only
kind of site this assignment touches.

**robots.txt check:** I requested `https://books.toscrape.com/robots.txt` once on
2026-11-13 (13:46 UTC). The server answered `HTTP/1.1 404 Not Found` — **no robots file found**.
A missing file is not permission, it is just a missing file; my permission comes from the
sandbox statement above.

**How much:** the first 3 catalogue pages only
(`/catalogue/page-1.html` to `/catalogue/page-3.html`), i.e. 60 books.

**What data I collect:** for each book listed on those pages — title, price, star rating,
stock availability, description, and the book's page URL. No personal data; the store and its books are fictional.

**Why this is appropriate:** the site was built specifically to be scraped for practice,
the data is fictional and public, and a three-page scope keeps the load on the server tiny.

I will not reuse this code on another site without checking its rules and terms first.

## How it works

1. **Discover** — start at `catalogue/page-1.html`, collect every book link, and follow the
   page's own "next" link until 3 pages are read. Relative links become absolute with
   `urljoin(page_url, href)`; duplicates are dropped.
2. **Extract** — fetch each book page and read the eight raw fields from the product area
   only (`article.product_page .product_main`), not "the first price on the page".
3. **Normalize and validate** — add `price_gbp` (a number) next to the raw `price_text`, then
   check every record against a Pydantic model **before** storing it.
4. **Store** — `books.json` is rebuilt each run, keyed by canonical `product_url`, so a rerun
   gives the same 60 records, not 120 (idempotent).
5. **Report** — every run ends by writing `run-report.json`.

Code: [`src/fetcher.py`](src/fetcher.py) (polite requests and cache),
[`src/parse.py`](src/parse.py) (HTML → data), [`src/schema.py`](src/schema.py) (schema and
normalization), [`src/main.py`](src/main.py) (the run).

## Record schema

Defined with [Pydantic](https://docs.pydantic.dev/) in [`src/schema.py`](src/schema.py)
(strict mode, no extra fields). Every field is required except `description`.

| Field | Type | Notes |
| --- | --- | --- |
| `title` | string, non-empty | |
| `product_url` | string, `https://` URL | canonical URL; the record's identity |
| `price_text` | string, non-empty | raw value as on the page, e.g. `"£51.77"` |
| `price_gbp` | number, ≥ 0 | clean value, e.g. `51.77` |
| `availability_text` | string, non-empty | e.g. `"In stock (22 available)"` |
| `rating_text` | `"One"` … `"Five"` | |
| `description` | string or `null` (optional) | `null` when the page has none; never invented |
| `source_page` | string, `https://` URL | provenance: the catalogue page the book was found on |
| `fetched_at` | ISO 8601 datetime | provenance: when the HTML was actually downloaded |

A record that fails goes to `output/errors.json` with the reason, e.g.
`price_gbp: Input should be a valid number`. It never reaches `books.json`.

## Politeness rules

- **Identifying user-agent** on every request:
  `FlyRankInternship-A9/1.0 (+https://github.com/kwibuloy/Flyrank_Week5)`.
- **Timeout:** a request gives up after 5 seconds.
- **Status check:** only `200` counts as a page; anything else is a failed fetch, not HTML to parse.
- **Delay:** at least 0.5 seconds between real requests. Cache hits skip the delay.
- **Cache:** each page is saved byte-for-byte to `cache/` and read from disk on later runs, so
  the site feels a full run once (63 requests) no matter how often the script is restarted.
- **Retries:** a timeout or `5xx` gets one more try after 2 seconds. A `404` or `403` is never retried.
- **Failure isolation:** each page is handled on its own; one broken page is logged and skipped.

## Proof: a real run report

From a fresh clone with an empty cache (`python src/main.py`, 2026-11-13):

```json
{
  "started_at": "2026-11-13T14:11:01.982Z",
  "finished_at": "2026-11-13T14:11:34.781Z",
  "duration_ms": 32799,
  "target": "https://books.toscrape.com/",
  "injected_broken_url": false,
  "catalogue_pages": 3,
  "discovered_urls": 60,
  "unique_urls": 60,
  "pages_fetched": 63,
  "cache_hits": 0,
  "retries": 0,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "failures": []
}
```

A rerun reads everything from cache (`pages_fetched: 0`, `cache_hits: 63`) and still
produces exactly 60 records.

**Why no browser:** the data is already in the HTML the server sends (the site needs no
JavaScript), so a headless browser would only add cost — more memory, slower runs, more
load — for no extra data. A plain HTTP request plus an HTML parser is enough.

## Honest limitation

The cache never expires. Once a page is in `cache/`, every later run reuses it, so if the
site changed a price tomorrow this scraper would keep reporting the old one until you
delete `cache/` (`fetched_at` does show how old each record's data is). The selectors are
also tied to this site's current markup; a redesign would break extraction, and the
schema would catch it as invalid records rather than silently storing bad data.

## Ethics note

Scraping should be the last resort, not the first. If a site offers an official API, use it.
Never get around a login, a paywall, a CAPTCHA, or a block: if a site has said no, the
answer is no. Collect only the data you actually need, identify yourself honestly, keep
your request rate low, and cache so you ask once. This project only works on a sandbox that
openly invites scraping, and it stays within three pages.
