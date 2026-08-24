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


# The order lifecycle as a state machine: each status maps to the statuses it
# may legally move to next. Illegal jumps (e.g. created -> paid, skipping
# payment) are refused, so a money action can never skip a step.
ORDER_TRANSITIONS = {
    "created": {"awaiting_payment", "cancelled"},
    "awaiting_payment": {"paid", "failed", "cancelled"},
    "paid": {"confirmed"},
    "confirmed": set(),                            # terminal: fulfilled
    "failed": {"awaiting_payment", "cancelled"},   # retry payment, or give up
    "cancelled": set(),                            # terminal: called off
}


class InvalidTransitionError(Exception):
    """Raised when an order is moved along an illegal status edge."""


# An order is the checkout of a saved cart — the money record. `status` tracks
# where it is in the checkout lifecycle, and set_status enforces the transitions
# allowed by ORDER_TRANSITIONS above.
class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cart_id: int = Field(foreign_key="cart.id")   # which cart this order is for
    amount: int                                    # total charged, in paise
    # Unique per checkout attempt: a retry with the same key returns the same
    # order instead of creating a duplicate (prevents accidental double orders).
    idempotency_key: str | None = Field(default=None, unique=True, index=True)
    status: str = "created"                        # lifecycle state; starts at "created"
    razorpay_order_id: str | None = None           # Razorpay's order id (test mode)
    payment_link_id: str | None = None             # Razorpay's payment link id
    payment_link_url: str | None = None            # the hosted pay page the buyer opens

    def set_status(self, new_status: str) -> None:
        """Move to new_status, but only if the state machine allows it."""
        if new_status not in ORDER_TRANSITIONS[self.status]:
            raise InvalidTransitionError(
                f"cannot move order from '{self.status}' to '{new_status}'"
            )
        self.status = new_status
