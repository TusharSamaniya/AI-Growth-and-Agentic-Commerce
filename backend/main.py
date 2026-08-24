import json

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.database import engine
from backend.llm import get_provider
from backend.models import Product
from backend.payments import apply_webhook_event, verify_webhook_signature

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


# Razorpay calls this the instant a payment event happens (the "push" that
# complements our polling). We verify the X-Razorpay-Signature first so a forger
# can't POST a fake "paid" event; only then do we act on it — advancing the
# matching order along the state machine. We take the raw Request because the
# signature check must hash the exact bytes Razorpay sent.
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="invalid signature")

    payload = json.loads(body)
    result = apply_webhook_event(payload)
    print("[webhook]", result)
    return {"status": "ok"}
