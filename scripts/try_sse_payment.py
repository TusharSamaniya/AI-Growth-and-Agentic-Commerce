# Proves the LIVE push end-to-end: subscribe to /events, then a (signed)
# payment_link.paid webhook marks the order paid, and the subscriber receives a
# "payment_received" event in real time — no polling.
#
# Needs the server running FROM THE PROJECT ROOT (so it shares cartpilot.db):
#     uvicorn backend.main:app --reload
# Then, also from the project root:  python -m scripts.try_sse_payment

import hashlib
import hmac
import json
import sys
import threading
import time
import uuid

import httpx

from backend.config import settings
from backend.payments import create_order
from backend.tools import build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000"

# 1) Create a real (TEST-MODE) order to pay. This writes to the same cartpilot.db
#    the running server reads, so its webhook handler will find this order.
cart = save_cart(build_cart([1])["items"])
order = create_order(cart, {"email": "buyer@example.com"}, True, f"sse-{uuid.uuid4()}")
print("Created order", order["id"], "status", order["status"])


# 2) Once we're subscribed, fire a signed payment_link.paid webhook at the server
#    (from a thread, so the main thread can stay parked on the stream).
def fire_webhook():
    time.sleep(1)  # let the subscription connect first — the bus doesn't replay
    payload = {
        "event": "payment_link.paid",
        "payload": {"payment_link": {"entity": {"id": order["payment_link_id"]}}},
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(
        settings.razorpay_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    httpx.post(f"{BASE}/webhook", content=body, headers={"X-Razorpay-Signature": signature})


threading.Thread(target=fire_webhook, daemon=True).start()

# 3) Subscribe and wait for the live payment_received push.
print("Subscribing to", f"{BASE}/events", "...")
with httpx.stream("GET", f"{BASE}/events", timeout=30) as response:
    for line in response.iter_lines():
        if line.startswith("data:"):
            print("received:", line)
            if "payment_received" in line:
                break
print("Got the live payment_received push — SSE is wired to the paid transition.")
