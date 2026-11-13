"""HTML parsing for Books to Scrape. Pure functions: HTML in, data out."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def clean(text: str | None) -> str | None:
    """Collapse whitespace; empty text becomes None (never invent a value)."""
    if text is None:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_catalogue(html: str, page_url: str) -> tuple[list[str], str | None]:
    """Return the absolute book links on one catalogue page, and its "next" link (if any)."""
    soup = BeautifulSoup(html, "html.parser")
    book_urls = [
        urljoin(page_url, a["href"]) for a in soup.select("article.product_pod h3 a[href]")
    ]
    next_link = soup.select_one("li.next a[href]")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return book_urls, next_url


def parse_book(html: str, *, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Read one book detail page into a raw record.

    Selectors are scoped to the product area (.product_main), not the whole
    document: the page also has a "Product Information" table with more prices.
    """
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("article.product_page") or BeautifulSoup("", "html.parser")
    main = product.select_one(".product_main") or BeautifulSoup("", "html.parser")

    def text_of(node) -> str | None:
        return clean(node.get_text()) if node else None

    rating_node = main.select_one("p.star-rating")
    rating = None
    if rating_node:
        rating = next((c for c in rating_node.get("class", []) if c != "star-rating"), None)

    # The description is the <p> right after the #product_description header.
    # Some books have none: store None (null in JSON), never invent text.
    header = product.select_one("#product_description")
    description_node = header.find_next_sibling("p") if header else None

    return {
        "title": text_of(main.select_one("h1")),
        "product_url": product_url,
        "price_text": text_of(main.select_one("p.price_color")),
        "availability_text": text_of(main.select_one("p.availability")),
        "rating_text": rating,
        "description": text_of(description_node),
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
