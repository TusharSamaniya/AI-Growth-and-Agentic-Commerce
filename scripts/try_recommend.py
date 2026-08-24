# Quick manual test of the recommend tool (fed by search_catalog).
# Run from the project root:  python -m scripts.try_recommend

import sys

from backend.tools import recommend, search_catalog

sys.stdout.reconfigure(encoding="utf-8")

# Step 1: find candidates (all phones). Step 2: rank them by a preference.
phones = search_catalog(filters={"category": "phone"})
picks = recommend(phones, preferences="5G 6GB 5000mAh", limit=3)

print(f"\nTop {len(picks)} picks for '5G 6GB 5000mAh':")
for p in picks:
    print(f"  {p['name']:<28} Rs {p['price'] / 100:>9,.2f}  - {p['reason']}")
