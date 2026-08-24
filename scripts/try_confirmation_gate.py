# Shows the confirmation gate: no order may be created without an explicit
# buyer confirmation of the exact cart, amount, and contact.
# Run from the project root:  python -m scripts.try_confirmation_gate

import sys

from backend.tools import ConfirmationError, build_cart, require_confirmation

sys.stdout.reconfigure(encoding="utf-8")

cart = build_cart([1])  # Redmi 12, Rs 8,999 -> {items, total, unavailable}
contact = {"email": "buyer@example.com"}


def check(label, **kwargs):
    try:
        require_confirmation(**kwargs)
        print(f"{label}: PASSED (order may be created)")
    except ConfirmationError as e:
        print(f"{label}: refused -> {e}")


# 1) Everything present and confirmed -> gate passes.
check("Valid confirmation", cart=cart, amount=cart["total"], contact=contact, confirmed=True)
# 2) Buyer never said yes -> refused.
check("Not confirmed", cart=cart, amount=cart["total"], contact=contact, confirmed=False)
# 3) Confirmed amount doesn't match the cart total -> refused.
check("Amount mismatch", cart=cart, amount=100000, contact=contact, confirmed=True)
# 4) No contact email -> refused.
check("Missing contact", cart=cart, amount=cart["total"], contact={}, confirmed=True)
