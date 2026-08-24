# Shows the budget cap ENFORCED at the data layer (not just flagged).
# build_cart computes the line items; save_cart refuses to persist an over-budget cart.
# Run from the project root:  python -m scripts.try_enforce_budget

import sys

from backend.tools import BudgetExceededError, build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

budget = 1000000  # Rs 10,000 in paise

# 1) Within budget: Redmi 12 (Rs 8,999) -> saved.
within = build_cart([1])
saved = save_cart(within["items"], budget)
print(f"Within budget -> saved cart #{saved['id']}, total Rs {saved['total'] / 100:.2f}")

# 2) Over budget: Motorola G34 5G + case + screen guard (Rs 10,497) -> refused.
over = build_cart([3, 5, 6])
try:
    save_cart(over["items"], budget)
    print("Over budget -> saved (BUG: cap not enforced!)")
except BudgetExceededError as e:
    print(f"Over budget -> refused: {e}")
