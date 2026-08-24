# Shows the webhook ACTING on verified events: a signed payment_link.paid moves
# our order to paid, and a signed payment.failed moves another to failed — no
# real payment or ngrok needed. We sign each event exactly as Razorpay would,
# then read the order status straight from the DB to prove it changed.
# Creates real TEST-mode Razorpay artifacts (test mode, no real money).
# Run from the project root:  python -m scripts.try_webhook_event

import hashlib
import hmac
import json
import sys
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.config import settings
from backend.database import engine
from backend.main import app
from backend.models import Order
from backend.payments import create_order
from backend.tools import build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

client = TestClient(app)
contact = {"email": "buyer@example.com"}


def post_webhook(payload: dict):
    """POST a payload to /webhook with a genuine Razorpay-style signature."""
    body = json.dumps(payload).encode()
    sig = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhook", content=body, headers={"X-Razorpay-Signature": sig})


def status_of(order_id: int) -> str:
    with Session(engine) as session:
        return session.get(Order, order_id).status


# --- Success: payment_link.paid (matched by our payment_link_id) -> paid ---
a = create_order(save_cart(build_cart([1])["items"]), contact, True, f"wh-{uuid.uuid4()}")
print("Order A created:", a["id"], "| status", a["status"])
r = post_webhook({
    "event": "payment_link.paid",
    "payload": {"payment_link": {"entity": {"id": a["payment_link_id"]}}},
})
print("  webhook ->", r.status_code, r.json())
print("  Order A status now:", status_of(a["id"]), "(expect paid)")

# --- Failure: payment.failed (matched by our razorpay_order_id) -> failed ---
b = create_order(save_cart(build_cart([1])["items"]), contact, True, f"wh-{uuid.uuid4()}")
print("Order B created:", b["id"], "| status", b["status"])
r = post_webhook({
    "event": "payment.failed",
    "payload": {"payment": {"entity": {"order_id": b["razorpay_order_id"]}}},
})
print("  webhook ->", r.status_code, r.json())
print("  Order B status now:", status_of(b["id"]), "(expect failed)")
