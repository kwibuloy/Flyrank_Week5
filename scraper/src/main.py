"""Entry point for the Books to Scrape scraper.

Target and scope are documented in ../README.md ("Target classification").
Scraping logic arrives in later stages.
"""

BASE_URL = "https://books.toscrape.com/"
MAX_PAGES = 3


def main() -> None:
    print(f"Target: {BASE_URL} (first {MAX_PAGES} catalogue pages only)")


if __name__ == "__main__":
    main()
