# Shows polling + state-machine sync: ask Razorpay for the payment link's status
# and advance our order to match (awaiting_payment -> paid on payment).
# No arg  -> create a fresh order, print its pay link, and poll once (still
#            awaiting_payment / razorpay "created", since nobody has paid).
# With id -> poll that order again (run it after paying the link in test mode to
#            watch OUR order flip awaiting_payment -> paid).
# Run from the project root:  python -m scripts.try_payment_status
#                        or:  python -m scripts.try_payment_status <order_id>

import sys
import uuid

from backend.payments import create_order, get_payment_status
from backend.tools import build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

if len(sys.argv) > 1:
    order_id = int(sys.argv[1])
    status = get_payment_status(order_id)
    print("Polled order", order_id)
    print("  our order status :", status["order_status"], "(synced from Razorpay)")
    print("  razorpay status  :", status["razorpay_status"])
    print(f"  amount paid      : Rs {status['amount_paid'] / 100:.2f}")
else:
    cart = save_cart(build_cart([1])["items"])  # Redmi 12, Rs 8,999
    order = create_order(cart, {"email": "buyer@example.com"},
                         confirmed=True, idempotency_key=f"poll-{uuid.uuid4()}")
    print("Created order", order["id"], "-> status", order["status"])
    print("Pay this link in test mode:", order["payment_link_url"])
    status = get_payment_status(order["id"])
    print("Polled now -> our status", status["order_status"],
          "| razorpay", status["razorpay_status"])
    print(f"\nAfter paying, re-run:  python -m scripts.try_payment_status {order['id']}")
