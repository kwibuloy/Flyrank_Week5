# Scraper

A small, polite web scraper built as a Week 5 internship exercise, written in Python.

## Run

```bash
pip install -r requirements.txt
python src/main.py
```

Requires Python 3.10+. HTML is parsed with [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/).
Downloaded pages are cached in `cache/` (git-ignored), so re-runs read from disk instead of hitting the site.

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
(`/catalogue/page-1.html` to `/catalogue/page-3.html`), i.e. at most 60 books.

**What data I collect:** for each book listed on those pages — title, price, star rating,
stock availability, description, and the book's page URL. No personal data; the store and its books are fictional.

**Why this is appropriate:** the site was built specifically to be scraped for practice,
the data is fictional and public, and a three-page scope keeps the load on the server tiny.

I will not reuse this code on another site without checking its rules and terms first.
