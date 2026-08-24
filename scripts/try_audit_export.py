# Proves GET /audit/{conversation_id}/export returns the audit trail as a
# downloadable JSON file (Content-Disposition: attachment) — the standalone
# artifact a judge can save and re-verify offline. Uses FastAPI's TestClient,
# so NO running server, Groq, or Razorpay is needed.
# Run from the project root (auditentry table must exist: python -m scripts.init_db):
#     python -m scripts.try_audit_export

import json
import sys
import uuid

from fastapi.testclient import TestClient

from backend.audit import record
from backend.main import app

sys.stdout.reconfigure(encoding="utf-8")

client = TestClient(app)
cid = f"audit-export-{uuid.uuid4()}"

# Lay down a small chain (no network — just the ledger).
record(cid, "buyer_message", {"text": "a 5G phone under 10000"})
record(cid, "order_created", {"order_id": 1, "amount": 899900})
record(cid, "status_change", {"order_id": 1, "from": "awaiting_payment", "to": "paid"})

# Hit the export endpoint.
response = client.get(f"/audit/{cid}/export")
print("GET /audit/", cid, "/export ->", response.status_code)
print("Content-Disposition:", response.headers.get("content-disposition"))

# Save a local copy to inspect — exactly the bytes a browser would download.
with open("audit-export.json", "wb") as f:
    f.write(response.content)
print("saved audit-export.json  (a sample artifact — safe to delete)")
print(json.dumps(response.json(), indent=2))
