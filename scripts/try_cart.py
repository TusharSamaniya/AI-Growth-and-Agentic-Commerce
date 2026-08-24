# Quick manual test of the build_cart tool.
# Run from the project root:  python -m scripts.try_cart

import sys

from backend.tools import build_cart

sys.stdout.reconfigure(encoding="utf-8")

# 2x Redmi 12 (id 1), 1x Silicone Back Case (id 6), and one bad id (999).
cart = build_cart([1, 1, 6, 999])

print("\nCart items:")
for item in cart["items"]:
    print(f"  {item['quantity']}x {item['name']:<24} Rs {item['line_total'] / 100:>9,.2f}")

print(f"  {'Total':<27} Rs {cart['total'] / 100:>9,.2f}")
print(f"  Unavailable: {cart['unavailable']}")
