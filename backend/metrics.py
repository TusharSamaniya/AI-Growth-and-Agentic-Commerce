# Merchant metrics: four numbers that quantify the revenue story, all computed
# from data the app already records (orders, carts, products, the audit trail).
# Read-only — this module never writes anything.

from sqlmodel import Session, select

from backend.database import engine
from backend.models import AuditEntry, Cart, Order, Product


def merchant_metrics() -> dict:
    """The four merchant KPIs. Safe on an empty database (returns zeros)."""
    with Session(engine) as session:
        orders = session.exec(select(Order)).all()
        products = session.exec(select(Product)).all()
        carts = {c.id: c.items for c in session.exec(select(Cart)).all()}
        # Every shopping session logs audit entries, so the distinct
        # conversation_ids there are our total sessions (the conversion base).
        conversation_ids = session.exec(select(AuditEntry.conversation_id)).all()

    total_conversations = len(set(conversation_ids))
    paid = [o for o in orders if o.status == "paid"]

    # 1. Conversion: sessions that ended in a paid order / all sessions.
    paid_conversations = {o.conversation_id for o in paid if o.conversation_id}
    conversion_rate = len(paid_conversations) / total_conversations if total_conversations else 0

    # 2. Avg basket size: the average value of a paid order, in paise.
    avg_order_value = sum(o.amount for o in paid) // len(paid) if paid else 0

    # 3. Upsell attach rate: of paid orders that had a phone, how many also had an
    #    accessory. Cart items carry the product id, so we map it to its category.
    phone_ids = {p.id for p in products if p.category == "phone"}
    accessory_ids = {p.id for p in products if p.category != "phone"}
    with_phone = with_addon = 0
    for o in paid:
        item_ids = {item["id"] for item in carts.get(o.cart_id, [])}
        if item_ids & phone_ids:
            with_phone += 1
            if item_ids & accessory_ids:
                with_addon += 1
    upsell_attach_rate = with_addon / with_phone if with_phone else 0

    # 4. Recovered carts: sessions that had a failed payment but ended paid.
    statuses = {}  # conversation_id -> the set of its order statuses
    for o in orders:
        if o.conversation_id:
            statuses.setdefault(o.conversation_id, set()).add(o.status)
    recovered_carts = sum(1 for s in statuses.values() if "failed" in s and "paid" in s)

    return {
        "conversion_rate": round(conversion_rate, 2),
        "avg_order_value": avg_order_value,
        "upsell_attach_rate": round(upsell_attach_rate, 2),
        "recovered_carts": recovered_carts,
        "paid_orders": len(paid),
        "total_conversations": total_conversations,
    }
