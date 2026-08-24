# Shows webhook signature verification: a genuine signature is accepted (200),
# a forged one is rejected (400) so a faker can't POST a fake "paid" event.
# We compute the genuine signature the SAME way Razorpay does: HMAC-SHA256 over
# the raw body using the shared webhook secret (settings.razorpay_webhook_secret;
# set RAZORPAY_WEBHOOK_SECRET in .env — the demo is self-consistent either way).
# Uses TestClient, so NO running server is needed.
# Run from the project root:  python -m scripts.try_webhook_signature

import hashlib
import hmac
import sys

from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app

sys.stdout.reconfigure(encoding="utf-8")

client = TestClient(app)
body = b'{"event":"payment_link.paid"}'

# Exactly what Razorpay signs: HMAC-SHA256(raw_body, webhook_secret).
good = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()

# 1) Genuine signature -> accepted.
r = client.post("/webhook", content=body, headers={"X-Razorpay-Signature": good})
print("Genuine signature ->", r.status_code, r.json())

# 2) Forged signature -> rejected, the event is NOT trusted.
r = client.post("/webhook", content=body, headers={"X-Razorpay-Signature": "forged"})
print("Forged signature  ->", r.status_code, r.json())
