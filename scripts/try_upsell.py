# Demonstrates bounded upsell: add-ons are offered ONLY when they fit the budget.
# The affordability check is done in Python (suggest_addons), not by the model.
# Run from the project root:  python -m scripts.try_upsell

import sys

from backend.agent import chat

sys.stdout.reconfigure(encoding="utf-8")

# Scenario 1: a cheap phone leaves room -> accessories should be offered.
q1 = "Add the Redmi 12 to my cart. My budget is 10000 rupees."
print("=== Scenario 1: budget has room (Redmi 12 = Rs 8,999) ===")
print("You:", q1)
print("Bot:", chat("upsell-room", q1))

# Scenario 2: a phone that eats the budget -> nothing should be pushed.
q2 = "Add the Motorola G34 5G to my cart. My budget is 10000 rupees."
print("\n=== Scenario 2: no room left (Motorola = Rs 9,999) ===")
print("You:", q2)
print("Bot:", chat("upsell-tight", q2))
