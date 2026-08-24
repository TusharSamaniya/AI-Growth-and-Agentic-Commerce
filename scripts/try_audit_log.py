# Proves the REAL flow now writes to the audit trail. Runs one agent turn,
# creates an order, and marks it paid via a webhook event — then prints the whole
# chain for that conversation and verifies it. Hits Groq (chat) and Razorpay
# (create_order, TEST mode), like the other agent/order demos. No server needed.
# Run from the project root, after `python -m scripts.init_db` rebuilds the schema:
#     python -m scripts.try_audit_log

import sys
import uuid

from sqlmodel import Session, select

from backend.agent import chat
from backend.audit import verify_chain
from backend.database import engine
from backend.models import AuditEntry
from backend.payments import apply_webhook_event, create_order
from backend.tools import build_cart, save_cart

sys.stdout.reconfigure(encoding="utf-8")

cid = f"audit-log-{uuid.uuid4()}"   # one conversation's trail

# 1) A buyer turn -> logs buyer_message, agent_decision(s), agent_reply.
reply = chat(cid, "I want a 5G phone under 10000, show me options.")
print("agent:", reply[:70].replace("\n", " "), "...\n")

# 2) A money action -> logs order_created (with the Razorpay ids).
cart = save_cart(build_cart([1])["items"])
order = create_order(cart, {"email": "buyer@example.com"}, True,
                     f"log-{uuid.uuid4()}", conversation_id=cid)
print("order", order["id"], "->", order["status"])

# 3) The paid webhook -> logs status_change (awaiting_payment -> paid).
apply_webhook_event({
    "event": "payment_link.paid",
    "payload": {"payment_link": {"entity": {"id": order["payment_link_id"]}}},
})

# Show the whole trail for this conversation, then verify it's intact.
with Session(engine) as session:
    entries = session.exec(
        select(AuditEntry).where(AuditEntry.conversation_id == cid).order_by(AuditEntry.id)
    ).all()

print("\nAudit trail:")
for e in entries:
    print(f"  #{e.id} {e.action:16} {e.data}")
print("\nverify_chain ->", verify_chain(cid))
