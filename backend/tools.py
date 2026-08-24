# Tools the agent can call during a conversation.
# Each is a plain Python function; Task 5.2 will describe them to the model as
# JSON schemas and run whichever one the model picks.

from collections import Counter

from sqlmodel import Session, or_, select

from backend.database import engine
from backend.models import Product


def search_catalog(
    query: str = "",
    max_price: int | None = None,
    filters: dict | None = None,
) -> list[dict]:
    """Find products by fuzzy text, a price ceiling (paise), and exact filters."""
    filters = filters or {}
    statement = select(Product)

    if query:
        like = f"%{query}%"
        statement = statement.where(
            or_(
                Product.name.like(like),
                Product.category.like(like),
                Product.brand.like(like),
                Product.specs.like(like),
            )
        )
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    if "category" in filters:
        statement = statement.where(Product.category == filters["category"])
    if "brand" in filters:
        statement = statement.where(Product.brand == filters["brand"])

    with Session(engine) as session:
        products = session.exec(statement).all()
    return [p.model_dump() for p in products]


def _searchable_text(p: dict) -> str:
    """All the words we match a preference against, lowercased."""
    return f"{p['name']} {p['category']} {p['brand']} {p['specs']}".lower()


def recommend(products: list[dict], preferences: str = "", limit: int = 3) -> list[dict]:
    """Rank products by how many preference words they match; cheapest wins ties.

    Returns the top `limit`, each with a `reason` explaining the pick.
    """
    words = preferences.lower().split()

    def match_count(p):
        return sum(1 for w in words if w in _searchable_text(p))

    ranked = sorted(products, key=lambda p: (-match_count(p), p["price"]))

    picks = []
    for p in ranked[:limit]:
        hits = [w for w in words if w in _searchable_text(p)]
        reason = f"matches {', '.join(hits)}" if hits else "budget-friendly option"
        picks.append({**p, "reason": reason})
    return picks


def build_cart(product_ids: list[int]) -> dict:
    """Assemble a cart from product IDs (repeat an ID for quantity > 1).

    Returns line items, a total in paise, and any unavailable IDs with a reason.
    """
    quantities = Counter(product_ids)  # {product_id: how many requested}
    items = []
    unavailable = []
    total = 0

    with Session(engine) as session:
        for product_id, quantity in quantities.items():
            product = session.get(Product, product_id)  # fetch by primary key
            if product is None:
                unavailable.append({"product_id": product_id, "reason": "not found"})
            elif product.stock < quantity:
                unavailable.append({"product_id": product_id, "reason": "out of stock"})
            else:
                line_total = product.price * quantity  # paise * count = paise
                total += line_total
                items.append({
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "quantity": quantity,
                    "line_total": line_total,
                })

    return {"items": items, "total": total, "unavailable": unavailable}
