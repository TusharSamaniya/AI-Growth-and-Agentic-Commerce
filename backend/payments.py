# The Razorpay adapter: the ONLY place in the app that talks to Razorpay.
# Every order passes the confirmation gate here BEFORE any money artifact is
# created, and the Razorpay ids are recorded on our own Order row.
# The raw Razorpay calls were de-risked in scripts/create_order.py and
# scripts/create_payment_link.py.

import razorpay
from sqlmodel import Session

from backend.config import settings
from backend.database import engine
from backend.models import Order
from backend.tools import require_confirmation

# One client for the app, authed with our TEST-MODE keys from .env.
_client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def create_order(cart: dict, contact: dict, confirmed: bool) -> dict:
    """Behind the confirmation gate, create a Razorpay order + payment link and
    persist an Order that records the Razorpay ids.

    `cart` must be a SAVED cart (from save_cart, so it has an id). Runs the
    governance check FIRST: require_confirmation raises if the buyer hasn't
    explicitly confirmed this exact cart, amount, and contact — so nothing is
    created without a valid confirmation. On success it creates the Razorpay
    order + payment link for the cart's exact total (paise), stores their ids on
    a new Order, moves it created -> awaiting_payment via the state machine, and
    returns the saved order.
    """
    amount = cart["total"]  # paise — Razorpay also works in paise
    require_confirmation(cart, amount, contact, confirmed)  # gate: raises if not OK

    rzp_order = _client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": "cartpilot_order",
    })
    link = _client.payment_link.create({
        "amount": amount,
        "currency": "INR",
        "description": "CartPilot order",
        "customer": {"email": contact["email"]},
    })

    # Record the Razorpay ids on our own order, then mark it awaiting payment.
    order = Order(
        cart_id=cart["id"],
        amount=amount,
        razorpay_order_id=rzp_order["id"],
        payment_link_id=link["id"],
        payment_link_url=link["short_url"],
    )
    order.set_status("awaiting_payment")  # created -> awaiting_payment: a link now exists

    with Session(engine) as session:
        session.add(order)
        session.commit()
        session.refresh(order)   # reload to get the database-assigned id
        return order.model_dump()
