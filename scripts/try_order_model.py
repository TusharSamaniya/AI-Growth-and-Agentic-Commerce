# Proves the Order model: save a cart, then create an order for it.
# A new order starts in status "created" (the state machine comes next).
# Run from the project root:  python -m scripts.try_order_model

import sys

from sqlmodel import Session

from backend.database import engine
from backend.models import Order
from backend.tools import build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

# Make a cart to order (Redmi 12, Rs 8,999).
cart = save_cart(build_cart([1])["items"])

order = Order(cart_id=cart["id"], amount=cart["total"])
with Session(engine) as session:
    session.add(order)
    session.commit()
    session.refresh(order)   # reload to get the database-assigned id
    order_id = order.id

# Read it back in a fresh session to prove it persisted, and check the default status.
with Session(engine) as session:
    saved = session.get(Order, order_id)
    print(f"Order #{saved.id} for cart #{saved.cart_id}")
    print(f"Amount: Rs {saved.amount / 100:.2f}")
    print(f"Status: {saved.status}")
