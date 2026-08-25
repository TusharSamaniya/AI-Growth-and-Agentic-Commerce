# PROJECT_PLAN.md — Conversational In-App Checkout Agent

> **Working title:** *CartPilot* — a conversational shopping agent that takes a buyer from
> "I want a budget phone under 10k" all the way to a confirmed, paid order in Razorpay
> **test-mode**, with every money action explained, bounded, gated, and audited.
>
> **Razorpay AI Buildathon · Track 01 — AI Growth & Agentic Commerce**
> **Direction:** Conversational in-app checkout · **Builder:** solo · **Timeline:** ~1 week

---

## 1. One-line pitch

A chat agent is the *only* interface the buyer touches. It understands intent, recommends
products, upsells intelligently, confirms the cart, drives the buyer into Razorpay's test
checkout, and confirms the order after payment — while a live, tamper-evident audit trail
proves that every money action was **explainable, bounded, and gated**, and that a payment
**failure is recovered gracefully**.

> **Key framing (important):** "the agent does everything end to end" means the buyer only
> talks to the agent and the agent *orchestrates* every step — product selection, order
> creation, and triggering the payment experience. **The agent never moves money directly.**
> All money movement happens inside Razorpay test-mode via our backend. This is exactly the
> "safe, bounded, gated" story the judges are asking for.

---

## 2. Why this wins — mapping to the judging bar

The track's bar is: *"Every money action explainable, bounded and gated. Show the audit
trail and one failure handled gracefully."* Most teams will show a chatbot that prints
"payment successful." We instead make the **governance around money** the visible star.

| Bar requirement | How CartPilot satisfies it |
|---|---|
| **Explainable** | Agent attaches a rationale to every recommendation *and* every money action (why this product, why this price, why this upsell). Rationales are stored and shown to judges in the audit panel. |
| **Bounded** | Buyer's stated budget ("under 10k") becomes a hard cap. Cart total, per-order cap, and upsell logic cannot breach the budget without an explicit re-confirmation. Merchant guardrails (max discount, allowed categories) enforced server-side. |
| **Gated** | No Razorpay order is created until the buyer explicitly confirms the final cart, amount, and contact details in chat. The confirmation step is the human-in-the-loop gate. |
| **Audit trail** | Append-only, **hash-chained** ledger records every buyer message, agent decision + rationale, cart, amount, Razorpay order/payment IDs, webhook events, and status transitions. Viewable live in the UI and exportable as JSON. |
| **Graceful failure** | Canonical demo: a test-mode payment declines → agent stays calm, explains, and offers retry / switch method / adjust cart → recovers to a confirmed order. **No money lost, fully logged.** |

**Extra merchant value story (revenue growth):** higher conversion (guided, low-friction
chat), larger basket size (smart upsell), and less drop-off (failure recovery). A small
merchant metrics panel quantifies this.

---

## 3. The end-to-end demo flow (the narrative judges see)

1. **Buyer:** "I want a budget phone under 10k."
2. **Agent:** suggests 2–3 phones within budget, each with a short **pros/cons rationale**.
3. **Agent asks 1–2 smart clarifying questions** ("camera or battery priority? brand
   preference?") to feel intelligent and to narrow the choice.
4. **Buyer picks one.** Agent proposes a **bounded upsell**: "Most buyers add a screen guard
   and case (₹499 total). Add them? You'd still be under your ₹10k budget."
5. **Buyer confirms final cart + contact details** in chat → **this is the gate.**
6. Agent calls backend → backend creates a **Razorpay test-mode order** and a
   **payment link** (or opens embedded Razorpay Checkout).
7. **Agent:** "Here's your secure Razorpay test checkout link — I'll wait while you pay."
8. **Buyer pays** in Razorpay's test checkout (test card / test UPI).
9. **Webhook** hits backend (fallback: status polling) → order marked **paid**.
10. **Agent:** "Payment received in test-mode ✅ Your order is confirmed. Order ID: …" with a
    summary. The audit panel shows the full internal trail.

**The failure branch (rehearsed):** at step 8 the buyer uses a **failure test card** → backend
receives `payment.failed` (or link stays unpaid past a timeout) → agent responds:
*"The payment didn't go through (card declined). No money has moved. Want to retry, switch to
UPI, or drop the accessories to lower the total?"* → buyer chooses → agent issues a fresh
payment link → success → confirmed. Every step logged.

---

## 4. Feature set

### 4.1 Core (MVP — must demo)
- Conversational agent with multi-turn memory (preferences, budget, cart).
- Agent-readable **catalog** (phones + accessories) with search & filter.
- **Smart recommendations** with explicit rationale and 1–2 clarifying questions.
- **Bounded upsell / cross-sell** (screen guard, case) that respects the budget.
- **Confirmation gate**: explicit cart + amount + contact confirmation before any order.
- **Razorpay test-mode**: create order → payment link (amount in paise) → payment.
- **Webhook receiver** with signature verification (fallback: **status polling**).
- Order **state machine**: `created → awaiting_payment → paid → confirmed` (+ `failed`).
- **Hash-chained audit ledger** + live audit panel in the UI.
- **One graceful failure** flow (payment decline → recover).
- React chat UI with product cards, cart summary, "waiting for payment," and a live
  "payment received" push (SSE/WebSocket).

### 4.2 Enhanced features (to impress — pick the ones that fit the week)
- **Idempotency keys** on order creation to prevent double charges (strong "safe money" signal).
- **Live payment status** pushed to the UI the instant the webhook fires (feels magical).
- **Merchant metrics mini-dashboard**: conversion rate, avg basket size, upsell attach rate,
  recovered-cart count — quantifies revenue growth.
- **Guardrail config** the merchant can set (max discount %, budget caps, allowed categories),
  enforced server-side and shown as "policy applied" in the audit.
- **Multiple failure modes handled**: out-of-stock at checkout, budget exceeded by upsell,
  expired link, duplicate payment, webhook signature mismatch (rejected).
- **Rich explanations**: structured `{action, params, rationale, expected_impact}` for every
  money action, rendered nicely for judges.

### 4.3 Stretch (only if ahead of schedule)
- Embedded Razorpay Checkout modal (more "in-app" feel than a link).
- Voice input for the chat.
- Simple product images in cards.
- Exportable audit report (PDF/JSON) as a "compliance" artifact.

---

## 5. The graceful failure flow (detailed)

**Trigger options in test-mode:** use a Razorpay **failure test card / test UPI failure**, let
the payment link **expire**, or have the buyer **cancel**.

**Detection:** `payment.failed` webhook, or `payment_link` not `paid` within a timeout, or a
status poll returning `failed`. Backend transitions order → `failed` and notifies the agent.

**Recovery (agent behavior):**
1. Stay calm and **explain**: "The payment didn't go through — the test card was declined. No
   money has moved."
2. Offer **bounded options**: (a) retry same method, (b) switch method (card ↔ UPI),
   (c) adjust cart (e.g., drop the upsell to reduce the total).
3. On choice, backend creates a **fresh payment link** (new idempotent order or safe reuse).
4. On success → confirm as normal.

**Audited:** the failure, the reason, the offered options, the buyer's choice, and the recovery
are all appended to the ledger — demonstrating "one failure handled gracefully" *with proof*.

---

## 6. System architecture

```
┌────────────────────┐        ┌──────────────────────────────────────────┐        ┌────────────────────┐
│   React Chat UI     │  HTTP  │              FastAPI backend               │  HTTP  │  Razorpay test-mode │
│  - chat + cards     │ <────> │  ┌──────────────────────────────────────┐  │ <────> │  - Orders API       │
│  - cart summary     │        │  │ Agent orchestrator                    │  │        │  - Payment Links    │
│  - "waiting to pay" │        │  │  (LLM via provider interface)         │  │        │  - Checkout         │
│  - live status (SSE)│        │  │  tools: search_catalog, recommend,    │  │        │  - Webhooks         │
│  - AUDIT PANEL      │        │  │         build_cart, create_order,     │  │        └─────────┬──────────┘
└─────────┬──────────┘        │  │         get_payment_status            │  │                  │ webhook
          │  SSE/WebSocket     │  └──────────────────────────────────────┘  │  <───────────────┘ (or poll)
          └───────────────────>│  Governance: budget bounding · gate ·      │
                               │              guardrails · idempotency       │
                               │  Order state machine                        │
                               │  Hash-chained AUDIT LEDGER                  │
                               │  SQLite (catalog, orders, audit)            │
                               └─────────────────────────────────────────────┘
```

**Component responsibilities**
- **Agent orchestrator** — runs the LLM loop, decides which tool to call, produces rationales.
  LLM is accessed through a `LLMProvider` interface so Groq and other hosted/local models are swappable.
- **Tools** — typed functions the agent calls. Money-affecting tools (`create_order`) route
  through the governance layer before touching Razorpay.
- **Governance** — enforces budget cap, confirmation gate, merchant guardrails, and idempotency.
- **Razorpay adapter** — creates orders (amount in **paise**), payment links; verifies webhook
  signatures; exposes status polling as a fallback.
- **Audit ledger** — append-only, each entry stores `prev_hash` + `hash(entry)` for tamper-evidence.
- **Realtime channel** — SSE/WebSocket pushes payment status to the UI without refresh.

---

## 7. Data model (SQLite for the demo)

- **product**: `id, name, category (phone|accessory), price_inr, brand, camera_score,
  battery_mah, stock, description, image_url`
- **conversation**: `id, created_at, buyer_budget_inr, preferences_json, state`
- **cart**: `id, conversation_id, items_json, subtotal_inr, total_inr`
- **order**: `id, cart_id, amount_paise, currency, razorpay_order_id, razorpay_payment_link_id,
  status (created|awaiting_payment|paid|failed|confirmed|cancelled), idempotency_key,
  created_at, updated_at`
- **audit_entry**: `id, ts, conversation_id, actor (buyer|agent|system|razorpay), event_type,
  payload_json, rationale, prev_hash, hash`

> **Money is stored in paise** in Razorpay calls (₹10,000 = `1000000` paise). Keep a clear
> INR ↔ paise conversion boundary to avoid off-by-100 bugs.

---

## 8. Agent design

- **Tool-calling loop** with a strict system prompt: the agent must (a) never exceed the
  buyer's stated budget without re-confirmation, (b) never create an order before an explicit
  confirmation, (c) attach a `rationale` to every recommendation and money action.
- **Tools (typed):**
  - `search_catalog(query, max_price, filters)` → products
  - `recommend(products, preferences)` → ranked shortlist + reasons
  - `build_cart(product_ids)` → cart with subtotal/total, budget check
  - `create_order(cart_id, contact)` → routes through governance → Razorpay order + link
  - `get_payment_status(order_id)` → current status
- **State the agent tracks:** budget, preferences, current cart, order status.
- **Every money action** is emitted as a structured object
  `{action, params, rationale, expected_impact}` and logged before execution.

---

## 9. LLM provider decision (Groq)

**Decision: build provider-agnostic; use Groq's free, OpenAI-compatible API as the model brain.**

- Define an `LLMProvider` interface (`chat(messages, tools) -> response`). Implementations:
  - **GroqProvider** — Groq Cloud, OpenAI-compatible API at `https://api.groq.com/openai/v1`,
    configured via `GROQ_API_KEY` + `GROQ_MODEL`.
    Model: **`openai/gpt-oss-20b`** (fast, generous free limits, strong tool-calling).
    Upgrade to **`openai/gpt-oss-120b`** if multi-step tool-calling needs more reasoning — a one-line `.env` change.
- **Why Groq:** zero local setup / no GPU, very fast inference, a free tier, and reliable
  function-calling — ideal for a solo builder on a one-week timeline.
- **Why still agnostic:** because Groq is OpenAI-compatible, any other OpenAI-compatible provider
  (or a local Ollama) can be swapped in later by changing the base URL + key — no app rewrite.
- **Key risk:** tool-calling reliability in multi-step flows → mitigated by tool-calling-strong
  models (gpt-oss) and keeping the model swappable via `GROQ_MODEL`.

---

## 10. Razorpay test-mode integration (verify exact params on Day 1)

- **Keys:** test API key id (`rzp_test_…`) + secret from the Razorpay dashboard.
- **Create order:** `POST /v1/orders` — `amount` (paise), `currency: "INR"`, `receipt`, `notes`.
- **Payment link (recommended for the chat metaphor):** `POST /v1/payment_links` — returns a
  `short_url` the agent shares; supports `callback_url` / notifications. Cleanest for
  "here's your link, I'll wait," and easy to reissue on failure.
- **Alt — embedded Checkout:** Razorpay Checkout (`checkout.js`) opens a modal in the React app
  using the `order_id` (more "in-app" feel; stretch).
- **Webhooks:** configure events (`payment.captured` / `payment_link.paid` / `payment.failed`);
  verify `X-Razorpay-Signature` with the webhook secret. **Local dev needs a public URL** →
  use an ngrok-style tunnel. **Fallback if tunneling is painful: poll the order/payment status
  API** — simpler and fully demoable.
- **Test payments:** use Razorpay's **test cards / test UPI** for success *and* failure to drive
  both the happy path and the failure demo.
- **Capture:** confirm whether payments auto-capture (order `payment_capture`) or need a manual
  capture call — decide on Day 1.

> **These endpoints/params are the intended design — confirm field names against the current
> Razorpay docs on Day 1 before building deeper.**

---

## 11. Tech stack

- **Backend:** Python + **FastAPI**, `razorpay` Python SDK, SQLite (via SQLModel/SQLAlchemy).
- **Agent/LLM:** provider-agnostic layer over **Groq** (OpenAI-compatible) + optional local/hosted model.
- **Realtime:** SSE (simplest) or WebSocket for live payment status.
- **Frontend:** **React** (Vite), a lightweight chat UI + product cards + audit panel.
- **Tunneling (if using webhooks):** ngrok or similar.
- **Audit:** append-only table with hash-chaining (SQLite) + JSON export.

---

## 12. One-week milestone plan (solo)

| Day | Focus | Outcome |
|---|---|---|
| **1** | **De-risk + scaffold** | Razorpay test account + keys; manually create an order, generate a payment link, complete a test payment, receive a webhook (via tunnel) *or* confirm status polling. Scaffold FastAPI + React + SQLite. Groq "hello tool-call" working. |
| **2** | **Catalog + audit foundation** | Seed phones + accessories; `search_catalog`/`recommend` tools; order data model + state machine; hash-chained audit ledger. |
| **3** | **Agent happy path** | Orchestrator + all tools wired; conversational flow: intent → recommend → clarify → upsell → **confirmation gate**; budget bounding enforced. |
| **4** | **Razorpay end-to-end** | create order → payment link → webhook/polling → mark paid → notify agent → confirm; SSE live status. |
| **5** | **React chat UI** | Chat, product cards, cart summary, "waiting for payment," live "payment received," **audit panel**. |
| **6** | **Graceful failure + polish** | Failure detection + agent recovery (retry / switch method / adjust cart); idempotency; extra guardrails; refine rationales. |
| **7** | **Impress + ship** | Merchant metrics panel (stretch); full rehearsal; demo video; README; bug-fix buffer. |

*(If time is tight, cut in this order: metrics panel → embedded Checkout → images. Never cut:
governance, audit trail, or the failure flow — those are the judging bar.)*

---

## 13. Day-1 de-risk checklist (do these before writing app code)

- [ ] Create Razorpay account, switch to **test-mode**, copy key id + secret.
- [ ] `create order` succeeds and returns an `order_id`.
- [ ] `create payment link` returns a `short_url`; open it and pay with a **test card**.
- [ ] Decide **webhook vs polling** (get a tunnel working, or confirm polling status transitions).
- [ ] Reproduce a **failed** test payment (failure test card) and observe the resulting status/event.
- [ ] Confirm **capture** behavior (auto vs manual).
- [ ] Groq tool-calling model reachable; a trivial `search_catalog` tool call round-trips.

---

## 14. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Webhooks hard to expose locally | Ship **status polling** as the default; treat webhooks as an enhancement. |
| Local LLM unreliable at tool-calling | Provider-agnostic layer; swap to a hosted model for the demo via one env var. |
| Paise/INR conversion bugs | Single conversion boundary; store paise for Razorpay, INR for display. |
| Double charges | **Idempotency keys** on order creation. |
| Scope creep (solo, 1 week) | Strict MVP vs stretch tiers; protect governance + audit + failure flow. |
| Demo brittleness | Rehearse the exact script; pre-seed catalog; record a backup video. |

---

## 15. Out of scope / anti-goals

- Real money, real card data, PCI concerns (test-mode only).
- Auth / accounts / multi-tenant merchant onboarding.
- Real protocol compliance (ACP/AP2/x402) — not needed for this direction.
- Production deployment, scaling, or a polished design system beyond a clean demo UI.

---

## 16. Definition of done

- A judge can watch: chat → recommendations (with reasons) → clarifying questions → bounded
  upsell → confirmation gate → Razorpay test payment → **live** confirmation.
- A judge can open the **audit panel** and see every step, rationale, amount, and Razorpay ID,
  hash-chained.
- A judge can watch the **failure demo**: payment declines → agent recovers → order confirmed →
  ledger shows no money lost.
- Runs locally with clear README steps; LLM swappable between Groq and other OpenAI-compatible/local models.

---

## 17. Open items (deferred)

- **Submission format** (repo / demo video / live demo requirements): to confirm on the
  buildathon site before the deadline. *(Deliberately deferred per builder's decision — build
  first.)*
- Confirm exact Razorpay endpoint field names and capture behavior on Day 1 (Section 13).

---

## 18. How we build this together (teaching workflow)

**Rules of engagement (agreed):**
1. This plan lists every **Phase → Task → Subtask** below.
2. **You pick one task** and tell me (e.g. "let's do Task 3.2").
3. I **explain** it first — what it is, why it matters, and how we'll approach it.
4. I **implement only that task** — the shortest, simplest, most readable code possible.
5. I **stop.** You read it, run it, and learn.
6. We move to the next task and repeat, from start to finish.

**Code-style promise:** short, simple, beginner-friendly — no clever tricks, no premature
abstraction, as few files as possible. Clarity over cleverness.

**Picking order:** phases are arranged so later ones build on earlier ones, so top-to-bottom is
the safe path — but the choice is yours. Tick the checkboxes as we complete each subtask.

**Status:** ✅ planning complete · ⬜ coding not started — nothing below is built yet.

---

## 19. Build plan — Phases → Tasks → Subtasks

### Phase 1 — Project setup & foundations
*Goal: a clean, runnable (empty) backend.*
- **Task 1.1 — Project structure & Python environment**
  - [x] Create a virtual environment (venv)
  - [x] Set up the folder layout (e.g. `backend/`, and `frontend/` later)
  - [x] Add `requirements.txt` and `.gitignore`
- **Task 1.2 — Minimal FastAPI server**
  - [x] Install `fastapi` + `uvicorn`
  - [x] Add a `GET /health` endpoint
  - [x] Run it and open it in the browser
- **Task 1.3 — Configuration & secrets**
  - [x] Create a `.env` file (Razorpay keys, model name)
  - [x] Load settings with `pydantic-settings`
  - [x] Make sure `.env` is git-ignored

### Phase 2 — De-risk the external services
*Goal: prove Razorpay and Groq work before building on them.*
- **Task 2.1 — Razorpay test-mode: first order & payment link (throwaway script)**
  - [x] Create a Razorpay account, switch to **test-mode**, copy test keys
  - [x] Install the `razorpay` Python SDK
  - [x] Script: create an order (amount in **paise**)
  - [x] Script: create a payment link, open it, pay with a **test card**
  - [x] Reproduce a **failed** payment with a failure test card
  - [x] Note capture behavior (auto vs manual)
    - **Capture** = when money actually moves: `authorized` (bank approved, funds held) → `captured` (funds collected). Uncaptured payments are **auto-refunded within ~3 days**.
    - **Auto-capture is Razorpay's default** (Dashboard: Account & Settings → Payments Capture). Manual capture needs an API call: `client.payment.capture(payment_id, amount, currency)`.
    - **Decision: CartPilot uses auto-capture** — the payment is confirmed the instant it succeeds, no `authorized` limbo. We detect success via payment/order `status` + webhook (Phase 7).
- **Task 2.2 — Groq: first chat & first tool-call**
  - [x] Set up Groq: add `GROQ_API_KEY` + `GROQ_MODEL` to `.env` and config; pick a tool-calling model
  - [x] Call the chat API from Python
  - [x] Get a trivial tool-call working (e.g. a fake `get_time` tool)

### Phase 3 — Data layer: catalog & database
*Goal: products stored in a database and searchable.*
- **Task 3.1 — Database & Product model**
  - [x] Add SQLite via SQLModel
  - [x] Define the `Product` model (name, category, price, brand, specs, stock)
  - [x] Create the database and tables
- **Task 3.2 — Seed the catalog**
  - [x] Write a seed script: a few phones + accessories (screen guard, case)
  - [x] Verify the rows exist
- **Task 3.3 — Catalog API**
  - [x] `GET /products` (list all)
  - [x] Filter by `max_price` and `category`
  - [x] Test the endpoint

### Phase 4 — LLM provider layer
*Goal: a swappable way to talk to the model (Groq now, other providers later).*
- **Task 4.1 — Define the `LLMProvider` interface**
  - [x] A base class/protocol with a `chat(messages, tools)` method
- **Task 4.2 — Implement `GroqProvider`**
  - [x] Wrap the Groq chat API
  - [x] Return a normalized response (text + any tool calls)
- **Task 4.3 — Simple `/chat` endpoint (no tools yet)**
  - [x] `POST /chat` → provider → reply
  - [x] Test a basic back-and-forth
- **Task 4.4 — (optional) `HostedProvider` fallback**
  - [x] Same interface, hosted model, switch via env var

### Phase 5 — The agent & tools (conversational core)
*Goal: the agent recommends, asks smart questions, and upsells — up to a chosen cart.*
- **Task 5.1 — Define the agent tools**
  - [x] `search_catalog(query, max_price, filters)`
  - [x] `recommend(products, preferences)`
  - [x] `build_cart(product_ids)`
- **Task 5.2 — The agent loop (tool-calling orchestration)**
  - [x] Send tools to the model, run the tool it picks, feed the result back
  - [x] Loop until the agent returns a final message
- **Task 5.3 — System prompt & conversation memory**
  - [x] Write the system prompt (rules: stay within budget, require confirmation, always give a rationale)
  - [x] Keep per-conversation message history
- **Task 5.4 — Smart recommendations + clarifying questions**
  - [x] Suggest 2–3 options with short pros/cons
  - [x] Ask 1–2 clarifying questions (camera vs battery, brand)
- **Task 5.5 — Bounded upsell**
  - [x] Propose add-ons that keep the total within budget
  - [x] Never breach the budget cap silently

### Phase 6 — Cart, orders & governance
*Goal: turn a confirmed cart into a Razorpay order — safely and on purpose.*
- **Task 6.1 — Cart model & budget bounding**
  - [x] `Cart` model (items, subtotal, total)
  - [x] Enforce the budget cap
- **Task 6.2 — Order model & state machine**
  - [x] `Order` model with a `status` field
  - [x] States: `created → awaiting_payment → paid → confirmed` (+ `failed` / `cancelled`)
- **Task 6.3 — The confirmation gate**
  - [x] Require explicit buyer confirmation (cart + amount + contact) before any order is created
- **Task 6.4 — `create_order` tool → Razorpay adapter**
  - [x] Run the governance check, then create the Razorpay order + payment link
  - [x] Store the Razorpay IDs on the order
- **Task 6.5 — Idempotency**
  - [x] Add an idempotency key to prevent accidental double orders

### Phase 7 — Payment status & realtime updates
*Goal: know the moment payment happens, and tell the UI instantly.*
- **Task 7.1 — `get_payment_status` tool + polling**
  - [x] Poll Razorpay for the order/link status
  - [x] Map it to the order state machine
- **Task 7.2 — Webhook receiver (optional; polling is the fallback)**
  - [x] `POST /webhook` endpoint
  - [x] Verify the `X-Razorpay-Signature`
  - [x] Update the order on `payment.captured` / `payment_link.paid` / `payment.failed`
- **Task 7.3 — Live updates via SSE**
  - [x] An SSE endpoint the UI subscribes to
  - [x] Push "payment received" when the order is paid

### Phase 8 — Audit trail (hash-chained ledger)
*Goal: prove every step happened, tamper-evident — the heart of the judging bar.*
- **Task 8.1 — `audit_entry` model + hash-chaining**
  - [x] Store `prev_hash` + `hash(entry)` for each entry
- **Task 8.2 — Log everything**
  - [x] Buyer messages, agent decisions + rationale, money actions, Razorpay responses, status changes
- **Task 8.3 — Audit query & export**
  - [x] `GET /audit/{conversation_id}`
  - [x] JSON export

### Phase 9 — Frontend: React chat UI
*Goal: the buyer-facing experience the judges actually watch.*
- **Task 9.1 — Vite + React setup**
  - [x] Scaffold the app and connect it to the backend
- **Task 9.2 — Chat interface**
  - [x] Message list + input box
  - [x] Send to `/chat`, render replies
- **Task 9.3 — Product cards & cart summary**
  - [ ] Render recommended products as cards
  - [ ] Show the current cart + total
- **Task 9.4 — Payment step**
  - [ ] Show the Razorpay payment link / button
  - [ ] A "waiting for payment…" state
- **Task 9.5 — Live confirmation via SSE**
  - [ ] Subscribe to SSE; show "Payment received ✅ — order confirmed"
- **Task 9.6 — Audit panel**
  - [ ] A side panel showing the live audit trail for judges

### Phase 10 — Graceful failure flow
*Goal: the "one failure handled gracefully" the bar explicitly asks for.*
- **Task 10.1 — Trigger & detect a failure**
  - [ ] Use a failure test card / let the link time out
  - [ ] Detect via webhook or polling → set the order to `failed`
- **Task 10.2 — Agent recovery**
  - [ ] Agent explains calmly ("no money moved")
  - [ ] Offers options: retry / switch method / adjust cart
- **Task 10.3 — Reissue & recover**
  - [ ] Create a fresh payment link; complete it successfully
- **Task 10.4 — Audit the failure & recovery**
  - [ ] Log the failure reason, the options offered, the choice, and the recovery

### Phase 11 — Polish & impress (stretch — pick what fits)
*Goal: the extras that lift a good demo to a winning one.*
- **Task 11.1 — Merchant metrics mini-dashboard** (conversion, avg basket size, upsell attach rate, recovered carts)
- **Task 11.2 — Merchant guardrail config** (max discount, caps, allowed categories) enforced server-side
- **Task 11.3 — Handle more failure modes** (out-of-stock, budget exceeded, expired link, duplicate payment, bad webhook signature)
- **Task 11.4 — Rich explanation rendering** (`{action, params, rationale, expected_impact}`)
- **Task 11.5 — (stretch) Embedded Razorpay Checkout modal** instead of a link

### Phase 12 — Rehearse & ship
*Goal: a reliable, repeatable demo.*
- **Task 12.1 — Full end-to-end rehearsal** (happy path + failure path)
- **Task 12.2 — README** with setup & run instructions
- **Task 12.3 — Record a demo video** (backup in case the live run glitches)
- **Task 12.4 — Bug-fix buffer & final cleanup**
