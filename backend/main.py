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


# Return the whole product catalog as JSON.
@app.get("/products")
def list_products():
    with Session(engine) as session:
        return session.exec(select(Product)).all()
