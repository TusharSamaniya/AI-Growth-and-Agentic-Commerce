# The Razorpay adapter: the ONLY place in the app that talks to Razorpay.
# Every order passes the confirmation gate here BEFORE any money artifact is
# created, and the Razorpay ids are recorded on our own Order row.
# The raw Razorpay calls were de-risked in scripts/create_order.py and
# scripts/create_payment_link.py.

import razorpay
from razorpay.errors import SignatureVerificationError
from sqlmodel import Session, select

from backend.config import settings
from backend.database import engine
from backend.models import ORDER_TRANSITIONS, Order
from backend.tools import require_confirmation

# One client for the app, authed with our TEST-MODE keys from .env.
_client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def create_order(cart: dict, contact: dict, confirmed: bool, idempotency_key: str) -> dict:
    """Behind the confirmation gate, create a Razorpay order + payment link and
    persist an Order that records the Razorpay ids.

    `cart` must be a SAVED cart (from save_cart, so it has an id).
    `idempotency_key` identifies this checkout attempt: if an order already
    exists for the key (a retry / double-click), that existing order is returned
    and NO second Razorpay order or payment link is created.

    Runs the governance check first: require_confirmation raises if the buyer
    hasn't explicitly confirmed this exact cart, amount, and contact — so nothing
    is created without a valid confirmation. On success it creates the Razorpay
    order + payment link for the cart's exact total (paise), stores their ids on
    a new Order, moves it created -> awaiting_payment, and returns the order.
    """
    # Idempotency: a retry with the same key returns the original order, never a
    # second order (or a second Razorpay charge).
    with Session(engine) as session:
        existing = session.exec(
            select(Order).where(Order.idempotency_key == idempotency_key)
        ).first()
        if existing:
            return existing.model_dump()

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
        idempotency_key=idempotency_key,
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


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """True if `signature` is Razorpay's real signature for these exact bytes.

    Razorpay signs each webhook with HMAC-SHA256 over the raw body using our
    shared webhook secret. We recompute it and compare: a match proves the call
    is genuinely from Razorpay AND the body wasn't tampered with. A forger
    without the secret can't produce a valid signature. Returns False instead of
    raising so the endpoint can simply reject with 400.
    """
    try:
        _client.utility.verify_webhook_signature(
            body.decode(), signature, settings.razorpay_webhook_secret
        )
        return True
    except SignatureVerificationError:
        return False


# How Razorpay's payment-link status maps onto our order state machine. Statuses
# not listed (created, partially_paid) mean "no change yet" — still awaiting.
RAZORPAY_TO_ORDER_STATUS = {
    "paid": "paid",
    "expired": "failed",
    "cancelled": "cancelled",
}


def get_payment_status(order_id: int) -> dict:
    """Poll Razorpay for the payment link's status and sync our order to match.

    The buyer pays via the payment link, so its status is the source of truth.
    We map that status onto our state machine and advance the order — but only
    along a LEGAL edge, so re-polling a paid order (paid -> paid, not allowed)
    or a terminal one simply does nothing instead of erroring.
    """
    with Session(engine) as session:
        order = session.get(Order, order_id)
        if order is None:
            return {"error": f"order {order_id} not found"}
        payment_link_id = order.payment_link_id

    # Network call kept outside the DB session on purpose.
    link = _client.payment_link.fetch(payment_link_id)
    razorpay_status = link["status"]

    # Map Razorpay's status onto our order and advance it — but only if that's a
    # legal transition from where the order is now (this makes polling idempotent).
    target = RAZORPAY_TO_ORDER_STATUS.get(razorpay_status)
    with Session(engine) as session:
        order = session.get(Order, order_id)
        if target and target in ORDER_TRANSITIONS[order.status]:
            order.set_status(target)   # still the enforcer of legal edges
            session.add(order)
            session.commit()
            session.refresh(order)
        our_status = order.status

    return {
        "order_id": order_id,
        "order_status": our_status,          # our state machine status (now synced)
        "razorpay_status": razorpay_status,  # created / paid / expired / cancelled
        "amount_paid": link["amount_paid"],  # paise actually paid so far
    }


# Which order status each webhook event drives us toward. Events not listed
# (e.g. payment.authorized) are ignored.
WEBHOOK_EVENT_TO_STATUS = {
    "payment_link.paid": "paid",
    "payment.captured": "paid",
    "payment.failed": "failed",
}


def apply_webhook_event(payload: dict) -> str:
    """Advance the matching order based on a VERIFIED webhook event.

    Finds our Order from the Razorpay ids the event carries — the payment link
    id for link events, the payment's order id for payment events — and moves it
    along the state machine (paid / failed). Only LEGAL transitions are applied,
    so a duplicate delivery (Razorpay retries until it gets a 2xx) is a harmless
    no-op. Unhandled events and unmatched orders are ignored. Returns a short
    summary string for the endpoint to log.
    """
    event = payload.get("event")
    target = WEBHOOK_EVENT_TO_STATUS.get(event)
    if target is None:
        return f"ignored {event}"

    # Different event families carry different ids; match our order on the right one.
    entities = payload.get("payload", {})
    if event == "payment_link.paid":
        match = Order.payment_link_id == entities["payment_link"]["entity"]["id"]
    else:  # payment.captured / payment.failed carry the paid order's id
        rzp_order_id = entities["payment"]["entity"].get("order_id")
        if rzp_order_id is None:
            return f"{event}: no order id in payload"
        match = Order.razorpay_order_id == rzp_order_id

    with Session(engine) as session:
        order = session.exec(select(Order).where(match)).first()
        if order is None:
            return f"no order matched {event}"
        if target not in ORDER_TRANSITIONS[order.status]:
            return f"{event}: order {order.id} already {order.status}"
        order.set_status(target)   # still the enforcer of legal edges
        session.add(order)
        session.commit()
        return f"{event}: order {order.id} -> {target}"
