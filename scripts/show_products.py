# Prints the catalog by reading it through SQLModel.
# Run from the project root:  python -m scripts.show_products

import sys

from sqlmodel import Session, select

from backend.database import engine
from backend.models import Product

# Windows terminals can't always print the ₹ symbol; force UTF-8 output.
sys.stdout.reconfigure(encoding="utf-8")

with Session(engine) as session:
    products = session.exec(select(Product)).all()

print(f"{len(products)} products in the catalog:")
for p in products:
    # price is stored in paise; divide by 100 to show rupees.
    print(f"  #{p.id}  {p.name:<28} ₹{p.price / 100:>10,.2f}  ({p.category}, stock {p.stock})")
