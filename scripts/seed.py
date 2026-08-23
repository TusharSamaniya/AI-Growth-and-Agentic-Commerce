# Fills the product table with a starter catalog.
# Run from the project root:  python -m scripts.seed

from sqlmodel import Session, select

from backend.database import engine
from backend.models import Product

# Prices are in PAISE (₹1 = 100 paise). So 899900 paise = ₹8,999.
products = [
    Product(name="Redmi 12", category="phone", brand="Xiaomi",
            price=899900, specs="4GB RAM, 128GB, 5000mAh", stock=10),
    Product(name="Realme Narzo 60", category="phone", brand="Realme",
            price=949900, specs="6GB RAM, 128GB, 90Hz display", stock=8),
    Product(name="Motorola G34 5G", category="phone", brand="Motorola",
            price=999900, specs="8GB RAM, 128GB, 5G", stock=6),
    Product(name="Samsung Galaxy M14", category="phone", brand="Samsung",
            price=1249900, specs="6GB RAM, 128GB, 6000mAh", stock=5),
    Product(name="Tempered Glass Screen Guard", category="screen_guard", brand="Generic",
            price=19900, specs="9H hardness, anti-scratch", stock=50),
    Product(name="Silicone Back Case", category="case", brand="Generic",
            price=29900, specs="Shockproof, matte finish", stock=40),
]

with Session(engine) as session:
    # Only seed if the table is empty, so re-running won't create duplicates.
    if session.exec(select(Product)).first():
        print("Catalog already has products — skipping seed.")
    else:
        session.add_all(products)
        session.commit()
        print(f"Seeded {len(products)} products.")
