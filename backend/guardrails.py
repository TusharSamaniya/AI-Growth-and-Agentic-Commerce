# Merchant guardrails: the shop owner's rulebook for what a checkout may do.
# This module only DEFINES and CHECKS the rules — it moves no money and writes
# nothing. The money gate (create_order) will call enforce_order() so a
# rule-breaking checkout is refused server-side, no matter what the agent tried.

from sqlmodel import Session

from backend.database import engine
from backend.models import Product

# The rulebook. A merchant edits these values; the server enforces them.
GUARDRAILS = {
    "max_order_amount": 10_000_000,  # cap on a single order, in paise (= Rs 1,00,000)
    "allowed_categories": ["phone", "case", "screen_guard", "charger", "earbuds", "power_bank"],
    "max_discount_percent": 10,      # declared policy; discounts aren't wired into carts yet
}


class GuardrailError(Exception):
    """Raised when a checkout would break one of the merchant's guardrails."""


def enforce_order(cart: dict) -> None:
    """Refuse (raise GuardrailError) if this cart breaks a guardrail; else pass.

    Checks the two rules we can enforce today:
      1. Order cap: the cart total must not exceed max_order_amount (paise).
      2. Allowed categories: every item's product category must be allowed.
    Returns None when the cart is within the rules, so create_order may proceed.
    """
    total = cart.get("total", 0)
    cap = GUARDRAILS["max_order_amount"]
    if total > cap:
        raise GuardrailError(f"order total {total} paise exceeds the cap of {cap} paise")

    allowed = set(GUARDRAILS["allowed_categories"])
    with Session(engine) as session:
        for item in cart.get("items", []):
            product = session.get(Product, item["id"])   # look up the item's category
            if product and product.category not in allowed:
                raise GuardrailError(
                    f"'{product.name}' is a '{product.category}', which the merchant does not sell"
                )
