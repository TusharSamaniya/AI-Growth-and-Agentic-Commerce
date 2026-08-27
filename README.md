# CartPilot 🛒✈️

A **conversational in-app checkout agent**. Shoppers chat in plain English —
*"I want a phone under ₹10,000"* — and the agent recommends, builds a cart,
suggests bounded add-ons, and takes them all the way to a **real Razorpay
(test-mode) payment**, then confirms the order.

Built for the **Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce**.

> **The bar:** *every money action is explainable, bounded and gated, with a
> tamper-evident audit trail and one failure handled gracefully.* CartPilot does
> exactly this:
> - **Gated** — only a human clicking **Confirm & Pay** creates a payment; the LLM can never move money.
> - **Bounded** — a merchant guardrail caps the order amount, allowed categories, and discount.
> - **Explainable** — every step is logged as *Action / Params / Why / Impact* with real numbers.
> - **Tamper-evident** — the audit log is a hash chain the UI marks **✔ Chain verified**.
> - **Graceful failure** — a declined payment opens a **Retry / Switch method / Adjust cart** recovery flow.

---

## Tech stack

| Layer     | Choice                                                              |
|-----------|--------------------------------------------------------------------|
| Backend   | Python + **FastAPI** (Uvicorn)                                     |
| Database  | **PostgreSQL** (via SQLModel + psycopg2)                           |
| LLM       | **Groq** (OpenAI-compatible), model `openai/gpt-oss-20b`          |
| Payments  | **Razorpay** test mode (orders, payment links, webhook, checkout) |
| Frontend  | **React 18 + Vite**                                               |

> Money is stored as integer **paise** (₹1 = 100 paise) and only formatted to ₹ for display.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for the Vite frontend)
- **PostgreSQL** running locally
- A **Razorpay test** account (Key ID + Key Secret) and a **Groq** API key

---

## Setup

### 1. Backend dependencies

From the project root:

```bash
python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Create the database

The app expects a database named `cartpilot`. Create it once (pgAdmin, or psql):

```sql
CREATE DATABASE cartpilot;
```

### 3. Configure secrets — `.env`

Create a file named `.env` in the project root. **Use your own keys** — this file
is git-ignored and must never be committed.

```env
# PostgreSQL (this default matches a standard local install)
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/cartpilot

# Razorpay TEST keys (dashboard → Settings → API Keys)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_razorpay_test_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret   # optional; only for live webhooks

# Groq LLM
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

> The **Key ID** is publishable (the browser needs it for the checkout popup, served via `/config`).
> The **Key Secret** stays on the server and is never exposed.

### 4. Create tables & seed the catalog

```bash
python -m scripts.init_db   # creates the tables in the cartpilot database
python -m scripts.seed      # fills the product catalog (phones + accessories)
```

`seed` only seeds when the table is empty. To refresh: run
`TRUNCATE public.product RESTART IDENTITY;` in pgAdmin, then re-run it.

### 5. Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Run

Open **two terminals** from the project root.

**Terminal 1 — backend (port 8000):**

```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — frontend (port 5173):**

```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173**.

Quick health check:

```bash
curl http://127.0.0.1:8000/health
```

Expect `{"status":"ok"}`.

---

## Try it (30-second happy path)

1. Type: **"I'm looking for a phone under ₹10,000."**
2. Add a phone: **"Add the Motorola G34 to my cart."**
3. Enter an email → click **Confirm & Pay**.
4. In the Razorpay popup, pay with test UPI `success@razorpay` (or card `4111 1111 1111 1111`).
5. Watch the order go **green** and the audit panel fill with verified steps.

For the full demo — including the **failure → recovery** path and the governance
checks — follow **[REHEARSAL.md](REHEARSAL.md)**.

---

## Project structure

```
backend/
  main.py        FastAPI app + all HTTP endpoints
  agent.py       the LLM agent loop (picks tools, logs every decision)
  tools.py       tools the agent can call (search, recommend, build cart…)
  guardrails.py  merchant limits (max amount, categories, discount)
  payments.py    Razorpay orders, links, webhook + checkout verification
  audit.py       hash-chained, tamper-evident audit ledger
  metrics.py     merchant KPIs (conversion, basket size, recovered carts)
  events.py      Server-Sent Events bus (live paid/failed updates)
  models.py      SQLModel tables + the order state machine
  database.py    PostgreSQL engine + table creation
  llm.py         LLM provider wiring (Groq / hosted)
  config.py      typed settings loaded from .env
frontend/
  src/App.jsx    the entire chat + cart + audit UI
scripts/
  init_db.py     create tables
  seed.py        seed the catalog
tests/           pytest suite
PROJECT_PLAN.md  the phased build plan
REHEARSAL.md     the end-to-end demo script
```

---

## Tests

```bash
pytest
```

---

## Notes

- **Test mode only** — Razorpay and Groq calls create real *test* artifacts; no real money moves.
- `/simulate/{order_id}/{outcome}` is a **dev-only** helper to force a paid/failed outcome
  locally without a public webhook tunnel; its audit entries are stamped `source: "simulated"`.
- Every page load starts a **fresh conversation** with its own audit trail.
