import asyncio
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.audit import audit_report
from backend.database import engine
from backend.events import subscribe, unsubscribe
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


# Return one conversation's audit trail, plus whether its hash chain is intact.
# This is the judging-bar payload: the full, ordered record of every buyer
# message, agent decision, money action and status change — with a "verified"
# flag proving nothing was altered after the fact. The Phase 9 audit panel reads
# this; a judge can hit it directly to inspect any conversation.
@app.get("/audit/{conversation_id}")
def audit(conversation_id: str):
    return audit_report(conversation_id)


# The same audit report, but delivered as a file download
# (Content-Disposition: attachment) — the standalone JSON artifact a judge can
# save and re-verify offline. The last entry's hash is the chain's anchor: keep
# this file and any later tampering with the live ledger won't match it.
@app.get("/audit/{conversation_id}/export")
def audit_export(conversation_id: str):
    report = audit_report(conversation_id)
    headers = {"Content-Disposition": f'attachment; filename="audit-{conversation_id}.json"'}
    return JSONResponse(report, headers=headers)


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


# Server-Sent Events: a one-way stream the UI subscribes to (browser side:
# new EventSource("/events")). Each connection subscribes to the pub/sub bus and
# forwards every published event as "data: ...\n\n". When an order is paid, the
# webhook publishes a "payment_received" event and it lands here instantly — no
# polling. If there's no news for 15s we send a keepalive comment to hold the
# connection open, and we unsubscribe when the client disconnects.
@app.get("/events")
async def events():
    queue = subscribe()

    async def stream():
        yield 'data: {"type": "connected"}\n\n'    # confirms the subscription is live
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {event}\n\n"      # a real published event
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"         # a comment line holds the connection open
        finally:
            unsubscribe(queue)                     # clean up when the client goes away

    return StreamingResponse(stream(), media_type="text/event-stream")
