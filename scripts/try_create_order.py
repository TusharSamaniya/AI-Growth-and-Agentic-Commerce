# Shows create_order end to end: the confirmation gate runs FIRST, then Razorpay
# creates a test-mode order + payment link, and the ids are stored on a new
# Order (moved created -> awaiting_payment). Creates real TEST artifacts on your
# Razorpay account (test mode, no real money).
# Run from the project root:  python -m scripts.try_create_order

import sys

from backend.payments import create_order
from backend.tools import ConfirmationError, build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

cart = save_cart(build_cart([1])["items"])  # Redmi 12, Rs 8,999 — saved so it has an id
contact = {"email": "buyer@example.com"}

# 1) No confirmation -> the gate blocks BEFORE any Razorpay call is made.
try:
    create_order(cart, contact, confirmed=False)
except ConfirmationError as e:
    print("Gate blocked (no Razorpay call made):", e)

# 2) Confirmed -> gate passes; Razorpay artifacts created and stored on the Order.
order = create_order(cart, contact, confirmed=True)
print("\nOrder saved behind the gate:")
print("  order id         :", order["id"])
print("  status           :", order["status"])
print("  cart id          :", order["cart_id"])
print("  razorpay_order_id:", order["razorpay_order_id"])
print("  payment_link_url :", order["payment_link_url"])
print(f"  amount           : Rs {order['amount'] / 100:.2f}")
