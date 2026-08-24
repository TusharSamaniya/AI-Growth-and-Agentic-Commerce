# Proves GET /audit/{conversation_id} returns a conversation's full audit trail
# plus a "verified" flag. Uses FastAPI's TestClient, so NO running server, Groq,
# or Razorpay is needed — it records a small chain directly, then queries the API.
# Run from the project root (the auditentry table must exist — run
# `python -m scripts.init_db` once if you haven't):
#     python -m scripts.try_audit_api

import json
import sys
import uuid

from fastapi.testclient import TestClient

from backend.audit import record
from backend.main import app

sys.stdout.reconfigure(encoding="utf-8")

client = TestClient(app)
cid = f"audit-api-{uuid.uuid4()}"

# Lay down a small chain (no network — just the ledger).
record(cid, "buyer_message", {"text": "a 5G phone under 10000"})
record(cid, "order_created", {"order_id": 1, "amount": 899900})
record(cid, "status_change", {"order_id": 1, "from": "awaiting_payment", "to": "paid"})

# Query the endpoint under test and print what a judge/UI would receive.
response = client.get(f"/audit/{cid}")
print("GET /audit/", cid, "->", response.status_code)
print(json.dumps(response.json(), indent=2))
