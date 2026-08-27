import asyncio
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.agent import active_cart, chat as agent_chat, last_cart, last_products
from backend.audit import audit_report, record
from backend.database import engine
from backend.events import subscribe, unsubscribe
from backend.guardrails import GuardrailError
from backend.metrics import merchant_metrics
from backend.models import Product
from backend.payments import apply_webhook_event, create_order, get_payment_status, simulate_payment_outcome, verify_webhook_signature
from backend.tools import ConfirmationError, save_cart

# Create the FastAPI application. This "app" is what Uvicorn runs.
app = FastAPI()

# Let the Vite dev frontend (http://localhost:5173) call this API from the
# browser. Without CORS the browser blocks these cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    # Match ANY localhost port (and 127.0.0.1) instead of hard-coding 5173. Vite
    # jumps to 5174/5175/... whenever the previous port is still in use, and the
    # dev page can be opened as either localhost or 127.0.0.1 — pinning one port
    # silently blocks the browser (the "Couldn't reach the agent" trap).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Merchant KPIs for the dashboard: conversion, avg order value, upsell attach
# rate, and recovered carts — all read-only, computed from data we already store.
@app.get("/metrics")
def metrics():
    return merchant_metrics()


# The shape of the JSON body POST /chat expects. conversation_id ties every turn
# (and its audit trail) to one buyer session; the frontend sends a fresh id per page.
class ChatRequest(BaseModel):
    conversation_id: str
    message: str


# Run one turn of the real agent: it picks tools, remembers this conversation, and
# logs every step to the audit trail. Returns the reply text, any products the
# agent surfaced, and the current cart — so the UI can render cards and a summary.
@app.post("/chat")
def chat(request: ChatRequest):
    reply = agent_chat(request.conversation_id, request.message)
    return {
        "reply": reply,
        "products": last_products(request.conversation_id),
        "cart": last_cart(request.conversation_id),
    }


# The shape POST /checkout expects: which conversation to check out, and the
# email where Razorpay sends the payment link.
class CheckoutRequest(BaseModel):
    conversation_id: str
    email: str
    attempt: int = 1  # which payment attempt; a retry bumps it for a fresh link


# The buyer's explicit "Confirm & Pay". This is the ONLY path that creates a
# money artifact, and it lives here as a plain endpoint — never as an LLM tool —
# so the model can't self-confirm and bypass the gate. `confirmed=True` here means
# "a human clicked Pay". We take the cart the agent last built for this
# conversation, persist it, and hand it to create_order, which runs the
# confirmation gate before creating the Razorpay order + payment link. The
# idempotency key is conversation_id + attempt number: a double-click (same
# attempt) returns the same order instead of charging twice, while a retry
# (bumped attempt) gets a FRESH key, so create_order mints a NEW payment link to
# recover from a failure instead of returning the failed order.
@app.post("/checkout")
def checkout(request: CheckoutRequest):
    cart = active_cart(request.conversation_id)  # persistent cart, safe across turns
    if not cart.get("items"):
        raise HTTPException(status_code=400, detail="no cart to check out")
    saved = save_cart(cart["items"])
    try:
        order = create_order(
            saved,
            {"email": request.email},
            confirmed=True,
            idempotency_key=f"{request.conversation_id}#{request.attempt}",
            conversation_id=request.conversation_id,
        )
    except (ConfirmationError, GuardrailError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "status": order["status"],
        "payment_link_url": order["payment_link_url"],
    }


# The polling fallback to the webhook: ask Razorpay for this order's payment-link
# status and sync our order to match. Unlike the webhook this needs no public
# tunnel — the browser can call it directly — so it always works in a local demo.
# It's how we DETECT a failure without depending on webhook delivery: an expired
# or cancelled link advances our order to `failed` / `cancelled` and records the
# status change in the audit trail. Only legal edges are taken, so re-polling a
# settled order is a safe no-op.
@app.get("/orders/{order_id}/status")
def order_status(order_id: int):
    return get_payment_status(order_id)


# DEV/DEMO ONLY — no money moves here. This is the manual twin of the Razorpay
# webhook: it fires the exact same "payment_received" / "payment_failed" event
# (plus the same order transition and audit entry) for one of OUR order ids, so
# the live paid / failed UI can be demoed locally without exposing /webhook
# through a public tunnel. The audit entry is stamped source "simulated" so the
# trail stays honest. Remove this route before any real deployment.
@app.post("/simulate/{order_id}/{outcome}")
def simulate(order_id: int, outcome: str):
    result = simulate_payment_outcome(order_id, outcome)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# The shape POST /recovery expects: which conversation, the order that failed,
# and which recovery option the buyer chose on the failed-payment panel.
class RecoveryRequest(BaseModel):
    conversation_id: str
    failed_order_id: int
    choice: str  # "retry" | "switch_method" | "adjust_cart"


# Log the buyer's recovery decision to the audit trail. The failure itself and
# the reissued order are already recorded (status_change -> failed, then a fresh
# order_created), so this fills the one gap the backend can't see on its own: the
# human choice made on the failed-payment panel — the options we offered and
# which one was picked. That completes the failure -> recovery story in the ledger.
@app.post("/recovery")
def recovery(request: RecoveryRequest):
    record(request.conversation_id, "recovery", {
        "failed_order_id": request.failed_order_id,
        "options": ["retry", "switch_method", "adjust_cart"],
        "choice": request.choice,
    })
    return {"status": "ok"}


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
        # A forged or tampered webhook. Log the rejection to a dedicated "system"
        # audit trail (never a buyer's — the body is attacker-controlled, so filing
        # it under a real conversation would let an attacker scribble in their
        # record) so even blocked attacks are on the tamper-evident ledger.
        record("system", "webhook_rejected", {"reason": "invalid signature"})
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
