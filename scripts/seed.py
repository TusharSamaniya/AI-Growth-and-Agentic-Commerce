# Fills the product table with a starter catalog.
# Run from the project root:  python -m scripts.seed
# Re-seeding: this only seeds when the table is EMPTY. To refresh the catalog,
# first clear it in pgAdmin's Query Tool:  TRUNCATE public.product RESTART IDENTITY;

from sqlmodel import Session, select

from backend.database import engine
from backend.models import Product

# Prices are in PAISE (₹1 = 100 paise). So 899900 paise = ₹8,999.
# Specs are kept full and consistent (RAM, storage, battery, camera, display,
# network) so the agent describes real facts instead of guessing.
products = [
    # --- Phones (budget → premium) ---
    Product(name="Redmi 12", category="phone", brand="Xiaomi",
            price=899900, specs="4GB RAM, 128GB, 5000mAh battery, 50MP camera, 90Hz display, 4G", stock=10),
    Product(name="Realme Narzo 60", category="phone", brand="Realme",
            price=949900, specs="6GB RAM, 128GB, 5000mAh battery, 64MP camera, 90Hz AMOLED, 4G", stock=8),
    Product(name="Motorola G34 5G", category="phone", brand="Motorola",
            price=999900, specs="8GB RAM, 128GB, 5000mAh battery, 50MP camera, 120Hz display, 5G", stock=6),
    Product(name="Samsung Galaxy M14", category="phone", brand="Samsung",
            price=1249900, specs="6GB RAM, 128GB, 6000mAh battery, 50MP camera, 90Hz display, 5G", stock=5),
    Product(name="POCO M6 Pro", category="phone", brand="Xiaomi",
            price=1099900, specs="8GB RAM, 256GB, 5000mAh battery, 64MP OIS camera, 120Hz AMOLED, 4G", stock=7),
    Product(name="iQOO Z9 5G", category="phone", brand="iQOO",
            price=1999900, specs="8GB RAM, 128GB, 5000mAh battery, 50MP OIS camera, 120Hz AMOLED, 5G", stock=6),
    Product(name="Nothing Phone (2a)", category="phone", brand="Nothing",
            price=2399900, specs="8GB RAM, 128GB, 5000mAh battery, 50MP dual camera, 120Hz AMOLED, 5G", stock=4),
    Product(name="Samsung Galaxy A55 5G", category="phone", brand="Samsung",
            price=3999900, specs="8GB RAM, 128GB, 5000mAh battery, 50MP OIS camera, 120Hz Super AMOLED, 5G", stock=3),
    Product(name="OnePlus 12R", category="phone", brand="OnePlus",
            price=4299900, specs="8GB RAM, 128GB, 5500mAh battery, 50MP camera, 120Hz LTPO AMOLED, 5G", stock=3),
    Product(name="Google Pixel 8a", category="phone", brand="Google",
            price=5299900, specs="8GB RAM, 128GB, 4492mAh battery, 64MP camera, 120Hz OLED, 5G", stock=2),

    # --- Cases ---
    Product(name="Silicone Back Case", category="case", brand="Generic",
            price=29900, specs="Shockproof, matte finish, precise cutouts", stock=40),
    Product(name="Spigen Rugged Armor Case", category="case", brand="Spigen",
            price=129900, specs="Military-grade drop protection, carbon-fiber texture", stock=25),
    Product(name="Clear Transparent Case", category="case", brand="Generic",
            price=19900, specs="Slim anti-yellowing TPU, wireless-charging friendly", stock=60),

    # --- Screen guards ---
    Product(name="Tempered Glass Screen Guard", category="screen_guard", brand="Generic",
            price=19900, specs="9H hardness, anti-scratch, case-friendly, easy install", stock=50),
    Product(name="Privacy Tempered Glass", category="screen_guard", brand="Generic",
            price=49900, specs="Anti-spy 28° view angle, 9H hardness", stock=30),
    Product(name="Matte Screen Protector", category="screen_guard", brand="Generic",
            price=34900, specs="Anti-glare, anti-fingerprint, smooth touch", stock=35),

    # --- Chargers ---
    Product(name="33W GaN Fast Charger", category="charger", brand="Generic",
            price=149900, specs="33W USB-C, GaN, compact travel charger", stock=20),
    Product(name="67W Fast Charger", category="charger", brand="Generic",
            price=199900, specs="67W USB-C, quick-charge compatible phones", stock=15),

    # --- Earbuds ---
    Product(name="boAt Airdopes 141", category="earbuds", brand="boAt",
            price=129900, specs="TWS earbuds, 42h playback, ENx mic, low latency", stock=30),
    Product(name="OnePlus Nord Buds 2", category="earbuds", brand="OnePlus",
            price=299900, specs="TWS, 12.4mm drivers, ANC, 36h playback", stock=18),

    # --- Power banks ---
    Product(name="10000mAh Power Bank", category="power_bank", brand="Generic",
            price=99900, specs="10000mAh, 22.5W fast charge, dual output", stock=25),
    Product(name="20000mAh Power Bank", category="power_bank", brand="Generic",
            price=179900, specs="20000mAh, 20W PD, USB-C in/out", stock=15),
]

with Session(engine) as session:
    # Only seed if the table is empty, so re-running won't create duplicates.
    if session.exec(select(Product)).first():
        print("Catalog already has products — skipping seed.")
        print("To refresh: run  TRUNCATE public.product RESTART IDENTITY;  in pgAdmin, then re-run this.")
    else:
        session.add_all(products)
        session.commit()
        print(f"Seeded {len(products)} products.")
