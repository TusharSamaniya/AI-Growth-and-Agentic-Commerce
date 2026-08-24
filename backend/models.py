from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


# A product in our catalog. `table=True` makes this a real database table.
class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    category: str          # e.g. "phone", "case", "screen_guard"
    brand: str
    price: int             # in paise: ₹1 = 100 paise, matches Razorpay
    specs: str             # short description, e.g. "6GB RAM, 128GB"
    stock: int             # how many units are available


# A saved shopping cart. Unlike the build_cart tool (which returns a throwaway
# dict mid-conversation), this is stored in the database so an Order can point
# at it and we keep an audit record of exactly what was bought, at what price.
class Cart(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Line items snapshotted from build_cart: [{id, name, price, quantity, line_total}].
    # Stored as one JSON column so the whole cart lives in a single row.
    items: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    subtotal: int = 0      # sum of line totals, in paise
    total: int = 0         # what the buyer pays, in paise (subtotal + shipping/discounts later)
