from fastapi import FastAPI
from sqlmodel import Session, select

from backend.database import engine
from backend.models import Product

# Create the FastAPI application. This "app" is what Uvicorn runs.
app = FastAPI()


# When someone sends a GET request to /health, run this function.
@app.get("/health")
def health():
    # FastAPI turns this dict into a JSON response automatically.
    return {"status": "ok"}


# Return products, optionally filtered by max_price (in paise) and/or category.
@app.get("/products")
def list_products(max_price: int | None = None, category: str | None = None):
    query = select(Product)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if category is not None:
        query = query.where(Product.category == category)
    with Session(engine) as session:
        return session.exec(query).all()
