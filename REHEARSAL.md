# CartPilot — Demo Rehearsal Script

Run this end-to-end before recording. Three parts:
**Happy path** (buy → pay → confirmed), **Failure path** (decline → recover), and a
**Governance showcase** for the judging bar. Tick each box as it passes; anything that
doesn't match the "expect" line is a finding to fix.

---

## 0. Prerequisites (once per session)

- [ ] PostgreSQL running; database `cartpilot` exists.
- [ ] Catalog seeded — run `python -m scripts.seed` (prints "Seeded 20 products." or "already has products").
- [ ] `.env` has the real Razorpay **test** keys, Groq key, `DATABASE_URL`, webhook secret.
- [ ] Backend on :8000 — `.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000`
- [ ] Frontend on :5173 (Vite).
- [ ] Open http://localhost:5173 — the metrics strip + an empty chat show.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

```bash
curl http://127.0.0.1:8000/config
```

Expect `{"status":"ok"}` and `{"razorpay_key_id":"rzp_test_..."}` (only the **public** key).

> Each page load = a **fresh conversation + audit trail**. Refresh to start a clean run.

---

## 1. Happy path (~2 min)

Type these in the chat, one message at a time:

- [ ] **"I'm looking for a phone under ₹10,000."** → agent recommends 2–3 phones *with reasons*; it may ask **one** clarifying question (camera vs battery, brand).
- [ ] (if asked) **"Battery life matters most, no brand preference."** → agent narrows to a pick.
- [ ] **"Add the Motorola G34 to my cart."** → cart appears (₹9,999). Agent may offer a **bounded add-on** (screen guard / case) that still fits the budget.
- [ ] (optional) **"Yes, add a screen guard and a case."** → cart updates, still under ₹10,000.
- [ ] In the **cart panel**: enter an email → click **Confirm & Pay ₹…**.
- [ ] Panel turns amber **"⏳ Waiting for payment…"** with a **Pay ₹… with Razorpay** button. Click it.
- [ ] The **Razorpay popup opens on the page** (not a new tab). Pay in test mode:
  - **UPI:** `success@razorpay`, or
  - **Card:** `4111 1111 1111 1111`, any future expiry, any CVV/OTP.
- [ ] Popup closes → panel flips **green: "✅ Payment received — order confirmed."**
- [ ] Metrics strip updates (conversion / basket size).

**Expect in the audit panel (right):** buyer messages · "Searched the catalog" · "Built the cart"
(*Impact* shows the real total) · "Created order & payment link" · "Payment status changed
awaiting_payment → paid" (*source: checkout*). Header reads **✔ Chain verified**.

---

## 2. Failure path (~1 min) — the graceful-recovery demo

Run a checkout up to the amber **"Waiting for payment…"** state (Part 1, but **don't pay**).
Note the order number shown ("Order #N").

Force a decline (deterministic):

```bash
curl -X POST http://127.0.0.1:8000/simulate/N/failed
```

- [ ] Panel flips **red: "⚠️ Payment didn't go through … no money moved."** with **Retry / Switch method / Adjust cart**.
- [ ] Click **Retry payment** → a fresh order + Pay button appear (new attempt = new link).
- [ ] Pay with the test **success** method → panel flips **green confirmed**.
- [ ] Metrics: **recovered carts** increments.

**Expect in audit:** status_change → failed (*source: simulated*) · a `recovery` entry (options
offered + your choice) · a new order_created · → paid. The full failure→recovery story, logged.

> **Authentic alternative:** instead of `/simulate`, pay with a Razorpay **failure test card** in
> the modal. `/simulate` is DEV-only and stamps the audit `source: "simulated"` so the ledger
> never pretends a real payment happened.

---

## 3. Governance showcase (the judging bar) — 4 quick hits

- [ ] **Bounded (over budget):** in a run where you said "under ₹10,000", then say
      **"Actually add the Google Pixel 8a"** (₹52,999). Cart shows **⚠️ … over budget** and there is
      **no Pay button** — an over-budget cart can't be paid.
- [ ] **Out of stock:** **"Add 5 Google Pixel 8a."** Cart shows **🚫 … out of stock** for it (only 2
      exist) — surfaced plainly, not silently dropped.
- [ ] **Gated (guardrail cap):** on a **fresh page** (no budget mentioned), say
      **"Add 2 Google Pixel 8a"** → total ₹1,05,998 → click **Confirm & Pay** → red server message:
      **"…above the single-order limit of Rs 1,00,000."** Audit logs `guardrail_blocked`.
- [ ] **Forged payment rejected:**

```bash
curl -i -X POST http://127.0.0.1:8000/payment/verify -H "Content-Type: application/json" -d "{\"order_id\":1,\"razorpay_order_id\":\"order_fake\",\"razorpay_payment_id\":\"pay_fake\",\"razorpay_signature\":\"deadbeef\"}"
```

  Expect **400 · invalid payment signature**. Then:

```bash
curl http://127.0.0.1:8000/audit/system
```

  → a `payment_verify_rejected` line. Even a **blocked** attack is on the ledger.

---

## 4. Audit panel — what to say to judges

- Every row is **explainable**: **Action / Params / Why / Impact** (with real numbers).
- **✔ Chain verified** = hash-chained, tamper-evident. Export a copy: `GET /audit/<conversation_id>/export`.
- Money actions are **gated** (confirmation + guardrail) and **bounded** (budget), and the **one
  failure is recovered** — all with proof, not just a "payment successful" toast.

---

## 5. Reset & troubleshooting

- **New run:** refresh the page (new conversation id + audit trail).
- **Stock ran low:** in pgAdmin run `TRUNCATE public.product RESTART IDENTITY;` then `python -m scripts.seed`.
- **Pay popup won't open:** hard-refresh (Ctrl+Shift+R) so `checkout.js` loads. If it's blocked, the
  button falls back to the hosted payment link — the sale still completes.
- **"Couldn't reach the agent":** check the backend terminal for a boxed traceback (usually the LLM
  call); retry the message.
