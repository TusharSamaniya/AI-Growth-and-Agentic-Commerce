# Demonstrates "never breach the cap silently": each item is individually cheap,
# but together they exceed the budget. build_cart flags it deterministically so
# the agent must surface the breach instead of hiding it.
#   Motorola G34 5G Rs 9,999 + case Rs 299 + screen guard Rs 199 = Rs 10,497 (> Rs 10,000)
# Run from the project root:  python -m scripts.try_over_budget

import sys

from backend.agent import chat

sys.stdout.reconfigure(encoding="utf-8")

q = ("My budget is 10000 rupees. Add the Motorola G34 5G, a silicone case, "
     "and a tempered glass screen guard to my cart.")
print("You:", q)
print("Bot:", chat("over-budget", q))
