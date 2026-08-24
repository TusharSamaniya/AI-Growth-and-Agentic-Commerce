# Shows the order state machine: legal steps advance, illegal jumps are refused.
# Happy path: created -> awaiting_payment -> paid -> confirmed.
# Pure in-memory (no DB needed) — it just exercises the transition rules.
# Run from the project root:  python -m scripts.try_order_states

import sys

from backend.models import InvalidTransitionError, Order

sys.stdout.reconfigure(encoding="utf-8")

order = Order(cart_id=1, amount=899900)  # status starts at "created"
print("Start:", order.status)

# Walk the happy path, one legal step at a time.
for nxt in ["awaiting_payment", "paid", "confirmed"]:
    order.set_status(nxt)
    print("  ->", order.status)

# Try an illegal jump on a fresh order: created -> paid (skips payment).
fresh = Order(cart_id=1, amount=899900)
try:
    fresh.set_status("paid")
    print("created -> paid allowed (BUG: state machine not enforced!)")
except InvalidTransitionError as e:
    print("Refused:", e)
