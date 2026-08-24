# Shows idempotency: calling create_order twice with the SAME key returns the
# SAME order — no second order and no second Razorpay charge. The retry
# short-circuits before any Razorpay call. Creates one real TEST artifact.
# Run from the project root:  python -m scripts.try_idempotency

import sys
import uuid

from backend.payments import create_order
from backend.tools import build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

cart = save_cart(build_cart([1])["items"])
contact = {"email": "buyer@example.com"}
key = f"checkout-{uuid.uuid4()}"   # one key for this checkout attempt

first = create_order(cart, contact, confirmed=True, idempotency_key=key)
second = create_order(cart, contact, confirmed=True, idempotency_key=key)  # retry, same key

print("First  -> order id", first["id"], "| razorpay", first["razorpay_order_id"])
print("Second -> order id", second["id"], "| razorpay", second["razorpay_order_id"])
print("Same order returned :", first["id"] == second["id"])
print("No second Razorpay  :", first["razorpay_order_id"] == second["razorpay_order_id"])
