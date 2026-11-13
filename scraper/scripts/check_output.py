"""Quick sanity check of output/books.json: count, numeric prices, https URLs, no duplicates.

Usage: python scripts/check_output.py
"""

import json
import math
import sys
from pathlib import Path

books_file = Path(__file__).resolve().parent.parent / "output" / "books.json"
books = json.loads(books_file.read_text(encoding="utf-8"))

problems = []
if len(books) != 60:
    problems.append(f"expected 60 records, found {len(books)}")

urls = {b["product_url"] for b in books}
if len(urls) != len(books):
    problems.append(f"{len(books) - len(urls)} duplicate product_url(s)")

for b in books:
    price = b.get("price_gbp")
    if not isinstance(price, (int, float)) or isinstance(price, bool) or math.isnan(price):
        problems.append(f"non-numeric price_gbp: {b['product_url']}")
    for key in ("product_url", "source_page"):
        if not str(b.get(key)).startswith("https://"):
            problems.append(f"{key} not https: {b.get(key)}")

print(f"records={len(books)}, unique_urls={len(urls)}")
if problems:
    print("FAIL\n- " + "\n- ".join(problems))
    sys.exit(1)
print("OK: 60 records, every price_gbp is a number, every URL starts with https://")
