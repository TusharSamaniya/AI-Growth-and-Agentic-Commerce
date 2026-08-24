# The audit ledger: a tamper-evident, hash-chained record of what happened.
# record() appends an entry linked to the one before it; verify_chain() proves
# the whole chain is intact. This module is the ONLY place that computes hashes,
# so the chaining rule lives in exactly one spot.
import hashlib
import json

from sqlmodel import Session, select

from backend.database import engine
from backend.models import AuditEntry


def _hash_entry(conversation_id: str, action: str, data: dict, prev_hash: str) -> str:
    """SHA-256 over the entry's content AND the previous hash.

    Folding prev_hash into the hash is what links each entry to the one before
    it: change any past entry and its hash changes, which breaks every entry
    after it too. sort_keys makes the JSON canonical so the same content always
    hashes the same way.
    """
    payload = json.dumps(
        {
            "conversation_id": conversation_id,
            "action": action,
            "data": data,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def record(conversation_id: str, action: str, data: dict) -> dict:
    """Append an entry to this conversation's chain and return it.

    Reads the conversation's most recent entry to get its hash (that becomes the
    new entry's prev_hash — or "" for the first, "genesis" entry), then stores
    this entry's own hash over its content + prev_hash.
    """
    with Session(engine) as session:
        last = session.exec(
            select(AuditEntry)
            .where(AuditEntry.conversation_id == conversation_id)
            .order_by(AuditEntry.id.desc())
        ).first()
        prev_hash = last.hash if last else ""   # genesis entry has no previous

        entry = AuditEntry(
            conversation_id=conversation_id,
            action=action,
            data=data,
            prev_hash=prev_hash,
            hash=_hash_entry(conversation_id, action, data, prev_hash),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry.model_dump()


def verify_chain(conversation_id: str) -> bool:
    """True if the conversation's chain is intact — nothing altered or reordered.

    Walks the entries in order, recomputing each hash from its stored content and
    checking two things: the entry links to the previous one (prev_hash matches),
    and its stored hash still equals what its content hashes to. Either mismatch
    means the ledger was tampered with after the fact.
    """
    with Session(engine) as session:
        entries = session.exec(
            select(AuditEntry)
            .where(AuditEntry.conversation_id == conversation_id)
            .order_by(AuditEntry.id)
        ).all()

    prev_hash = ""
    for entry in entries:
        expected = _hash_entry(entry.conversation_id, entry.action, entry.data, prev_hash)
        if entry.prev_hash != prev_hash or entry.hash != expected:
            return False
        prev_hash = entry.hash
    return True
