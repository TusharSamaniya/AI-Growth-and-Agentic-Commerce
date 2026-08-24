# Proves the audit ledger is tamper-evident. Records a few entries, prints the
# hash chain, verifies it, then edits one entry directly in the DB (as an
# attacker would) and shows verification catch it.
# Run from the project root, after `python -m scripts.init_db` creates the new
# table:  python -m scripts.try_audit_chain

import sys
import uuid

from sqlmodel import Session, select

from backend.audit import record, verify_chain
from backend.database import engine
from backend.models import AuditEntry

sys.stdout.reconfigure(encoding="utf-8")

cid = f"audit-demo-{uuid.uuid4()}"   # a fresh chain each run

# 1) Append a few entries — the kind of things Task 8.2 will log for real.
record(cid, "buyer_message", {"text": "phone under 10000"})
record(cid, "order_created", {"order_id": 1, "amount": 899900})
record(cid, "payment_received", {"order_id": 1})


def show_chain():
    with Session(engine) as session:
        entries = session.exec(
            select(AuditEntry).where(AuditEntry.conversation_id == cid).order_by(AuditEntry.id)
        ).all()
    for e in entries:
        prev = e.prev_hash[:8] if e.prev_hash else "(genesis)"
        print(f"  #{e.id} {e.action:16} prev={prev:11} hash={e.hash[:8]}")


print("Chain:")
show_chain()
print("verify_chain ->", verify_chain(cid))   # expect True

# 2) Tamper: edit the middle entry's data directly, WITHOUT fixing its hash —
#    exactly what a sneaky after-the-fact edit to the ledger looks like.
with Session(engine) as session:
    entries = session.exec(
        select(AuditEntry).where(AuditEntry.conversation_id == cid).order_by(AuditEntry.id)
    ).all()
    entries[1].data = {"order_id": 1, "amount": 100}   # "someone" lowered the amount
    session.add(entries[1])
    session.commit()

print("\nAfter tampering with entry #2's amount:")
print("verify_chain ->", verify_chain(cid))   # expect False — caught!
