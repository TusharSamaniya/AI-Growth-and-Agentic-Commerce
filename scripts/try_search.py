# Quick manual test of the search_catalog tool.
# Run from the project root:  python -m scripts.try_search

import sys

from backend.tools import search_catalog

sys.stdout.reconfigure(encoding="utf-8")  # let Windows print the rupee symbol


def show(label, results):
    print(f"\n{label} -> {len(results)} match:")
    for p in results:
        print(f"  {p['name']:<28} Rs {p['price'] / 100:>9,.2f}  ({p['category']}, {p['brand']})")


# 1) Budget phones under Rs 10,000 (max_price is in paise: 10000 * 100 = 1000000).
show("Budget phones under 10000", search_catalog(max_price=1000000, filters={"category": "phone"}))

# 2) Free-text search across all columns.
show("Text search 'case'", search_catalog(query="case"))
