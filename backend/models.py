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
