# Proves the Cart model persists: save a cart, then read it back in a fresh session.
# Run from the project root:  python -m scripts.try_cart_model

import sys

from sqlmodel import Session

from backend.database import engine
from backend.models import Cart

sys.stdout.reconfigure(encoding="utf-8")

# A sample cart — the item shape matches what the build_cart tool returns.
items = [{"id": 1, "name": "Redmi 12", "price": 899900, "quantity": 1, "line_total": 899900}]
subtotal = sum(i["line_total"] for i in items)
cart = Cart(items=items, subtotal=subtotal, total=subtotal)

with Session(engine) as session:
    session.add(cart)
    session.commit()
    session.refresh(cart)   # reload so we get the id the database assigned
    cart_id = cart.id

# Read it back in a NEW session to prove it truly persisted to the file.
with Session(engine) as session:
    saved = session.get(Cart, cart_id)
    print(f"Saved cart #{saved.id}")
    print("Items:", saved.items)
    print(f"Subtotal: Rs {saved.subtotal / 100:.2f}")
    print(f"Total:    Rs {saved.total / 100:.2f}")
