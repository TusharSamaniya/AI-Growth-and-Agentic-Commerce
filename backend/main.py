from fastapi import FastAPI
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.database import engine
from backend.llm import get_provider
from backend.models import Product

# Create the FastAPI application. This "app" is what Uvicorn runs.
app = FastAPI()

# Build the LLM provider once at startup (chosen by LLM_PROVIDER) and reuse it.
provider = get_provider()


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


# The shape of the JSON body that POST /chat expects: {"message": "..."}.
class ChatRequest(BaseModel):
    message: str


# Send one user message to the model and return its normalized reply.
@app.post("/chat")
def chat(request: ChatRequest):
    messages = [{"role": "user", "content": request.message}]
    return provider.chat(messages)
