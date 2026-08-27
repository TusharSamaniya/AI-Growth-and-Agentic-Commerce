import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

// Format a paise integer as rupees, e.g. 899900 -> "₹8,999".
const rupees = (paise) => `₹${(paise / 100).toLocaleString("en-IN")}`;

// A light background color per audit action, so judges can scan the trail by type.
const ACTION_COLOR = {
  buyer_message: "#e7f1ff",
  agent_decision: "#efe7ff",
  agent_reply: "#e9ecef",
  order_created: "#fff3cd",
  status_change: "#e6f4ea",
  recovery: "#ffe8cc",
  guardrail_blocked: "#ffe3e3",
};

// A short, human-readable line for one audit entry, based on its action + data.
function summarize(entry) {
  const d = entry.data || {};
  switch (entry.action) {
    case "buyer_message": return d.text;
    case "agent_reply": return d.text;
    case "agent_decision": return `tool: ${d.tool}`;
    case "order_created": return `order #${d.order_id} · ${rupees(d.amount)} · ${d.status}`;
    case "status_change": {
      const reason = d.razorpay_status || d.event;   // the failure/settlement reason, if any
      return `${d.from} → ${d.to}${reason ? ` (${reason})` : ""}`;
    }
    case "recovery": return `chose "${d.choice}" · offered ${(d.options || []).join(" / ")}`;
    case "guardrail_blocked": return d.reason;
    default: return JSON.stringify(d);
  }
}

// A rich, human explanation of one audit entry: what happened, the key numbers,
// WHY it happened, and the expected impact — all derived from data we already
// record (never guessed). Returns null for plain chat lines, which show as text.
function explain(entry) {
  const d = entry.data || {};
  switch (entry.action) {
    case "agent_decision":
      return explainTool(d.tool, d.arguments || {}, d.result);
    case "order_created":
      return {
        action: "Created order & payment link",
        params: `Order #${d.order_id} · ${rupees(d.amount)}`,
        rationale: "Buyer confirmed the cart and clicked Pay",
        expected_impact: "Razorpay link issued; order now awaiting payment",
      };
    case "status_change": {
      const reason = d.razorpay_status || d.event;
      const impact = d.to === "paid" ? "Order confirmed — money received"
        : d.to === "failed" ? "Buyer offered recovery options"
        : d.to === "cancelled" ? "Order called off; nothing charged"
        : "Order advanced along its lifecycle";
      return {
        action: "Payment status changed",
        params: `${d.from} → ${d.to}`,
        rationale: `Reported by ${d.source}${reason ? ` (${reason})` : ""}`,
        expected_impact: impact,
      };
    }
    case "recovery":
      return {
        action: "Buyer chose a recovery option",
        params: d.choice,
        rationale: "The previous payment attempt failed",
        expected_impact: d.choice === "adjust_cart"
          ? "Back to the cart to change items, then pay again"
          : "A fresh payment link is issued to try again",
      };
    case "guardrail_blocked":
      return {
        action: "Checkout blocked (guardrail)",
        params: rupees(d.amount),
        rationale: d.reason,
        expected_impact: "No order created; buyer told why",
      };
    case "webhook_rejected":
      return {
        action: "Forged webhook rejected",
        params: d.reason,
        rationale: "Signature didn't match our secret — not really from Razorpay",
        expected_impact: "Fake payment blocked; nothing charged",
      };
    default:
      return null; // buyer_message / agent_reply -> plain text
  }
}

// The four fields for one agent tool-call decision.
function explainTool(tool, args, result) {
  switch (tool) {
    case "search_catalog":
      return {
        action: "Searched the catalog",
        params: args.query ? `"${args.query}"` : "all products",
        rationale: "Looks up real products before answering — never invents them",
        expected_impact: result || "Finds matching products to recommend",
      };
    case "recommend":
      return {
        action: "Ranked recommendations",
        params: args.preferences ? `by "${args.preferences}"` : "by best fit",
        rationale: "Matches products to what the buyer asked for",
        expected_impact: result || "Shows the best few options, each with a reason",
      };
    case "build_cart":
      return {
        action: "Built the cart",
        params: `${(args.product_ids || []).length} item(s)${args.budget ? ` · budget ${rupees(args.budget)}` : ""}`,
        rationale: "Buyer selected these products",
        expected_impact: result || "Cart shown for confirmation before any payment",
      };
    case "suggest_addons":
      return {
        action: "Suggested add-ons",
        params: args.budget ? `within ${rupees(args.budget)} budget` : "within budget",
        rationale: "Only accessories that fit the remaining budget",
        expected_impact: result || "Bounded upsell — never pushes the total over budget",
      };
    default:
      return { action: `Tool: ${tool}`, params: JSON.stringify(args), rationale: "Agent step", expected_impact: result || "—" };
  }
}

// The four merchant KPIs, shown as a live strip of stat tiles across the top.
function MetricsStrip({ metrics }) {
  if (!metrics) return null;
  const pct = (x) => `${Math.round(x * 100)}%`;
  const tiles = [
    { label: "Conversion", value: pct(metrics.conversion_rate) },
    { label: "Avg order value", value: rupees(metrics.avg_order_value) },
    { label: "Upsell attach rate", value: pct(metrics.upsell_attach_rate) },
    { label: "Recovered carts", value: metrics.recovered_carts },
  ];
  return (
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
      {tiles.map((t) => (
        <div key={t.label} style={{ flex: 1, minWidth: 130, border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, color: "#888" }}>{t.label}</div>
          <div style={{ fontSize: 22, fontWeight: "bold", marginTop: 4 }}>{t.value}</div>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]); // each: { role: "user" | "assistant", text }
  const [input, setInput] = useState("");
  const [products, setProducts] = useState([]);      // the agent's latest recommendations
  const [cart, setCart] = useState(null);            // the current cart (from build_cart)
  const [cid] = useState(() => crypto.randomUUID()); // one conversation (+ audit trail) per page load
  const [busy, setBusy] = useState(false);           // true while waiting for the agent's reply
  const [email, setEmail] = useState("test@example.com"); // where Razorpay sends the payment link
  const [order, setOrder] = useState(null);          // the checkout result (Razorpay payment link)
  const [paying, setPaying] = useState(false);       // true while /checkout is in flight
  const [attempt, setAttempt] = useState(1);         // payment attempt #; a retry bumps it for a fresh link
  const [checkoutError, setCheckoutError] = useState(""); // a calm message if checkout fails
  const [paidOrderId, setPaidOrderId] = useState(null);   // which order the live event told us is paid
  const [failedOrderId, setFailedOrderId] = useState(null); // which order the live event told us failed
  const [audit, setAudit] = useState(null);               // this conversation's audit trail (polled live)
  const [razorpayKey, setRazorpayKey] = useState("");     // public Razorpay Key ID for the on-page modal

  // Subscribe to the server's live event stream. When the payment webhook fires,
  // the backend publishes a "payment_received" or "payment_failed" event, and it
  // arrives here instantly (no polling); we note the order id and the render reacts.
  useEffect(() => {
    const es = new EventSource(`${API}/events`);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "payment_received") setPaidOrderId(data.order_id);
        if (data.type === "payment_failed") setFailedOrderId(data.order_id);
      } catch {
        // ignore keepalives and any non-JSON frames
      }
    };
    return () => es.close(); // close the stream when the page goes away
  }, []);

  // Fetch the public Razorpay Key ID once, so the embedded Checkout modal can open
  // with it. It's the publishable key (safe in the browser); the secret stays server-side.
  useEffect(() => {
    fetch(`${API}/config`)
      .then((r) => r.json())
      .then((c) => setRazorpayKey(c.razorpay_key_id))
      .catch(() => {}); // if it fails, the Pay button falls back to the payment link
  }, []);

  // Poll the audit trail so the side panel stays live as the conversation grows —
  // this catches every server-side change, including the webhook's status update.
  useEffect(() => {
    const load = () =>
      fetch(`${API}/audit/${cid}`)
        .then((r) => r.json())
        .then(setAudit)
        .catch(() => {}); // a transient miss just leaves the last trail on screen
    load();
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, [cid]);

  // The merchant metrics for the top strip: kept in state and polled every few
  // seconds so the KPIs update live as orders get paid or recovered.
  const [metrics, setMetrics] = useState(null);
  useEffect(() => {
    const load = () =>
      fetch(`${API}/metrics`)
        .then((r) => r.json())
        .then(setMetrics)
        .catch(() => {}); // a transient miss just keeps the last numbers on screen
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, []);

  // While an order is awaiting payment, poll its REAL status straight from
  // Razorpay. A link that expires or is cancelled sends no webhook, so without
  // this the screen would hang on "Waiting…" forever; polling also lets a locally
  // run app confirm a real payment with no public webhook tunnel. The moment the
  // order resolves we set the same paid/failed state the SSE events use (so the
  // existing panels react), then this effect re-runs, hits the guard, and stops.
  useEffect(() => {
    if (!order) return;                                                        // nothing to watch yet
    if (order.order_id === paidOrderId || order.order_id === failedOrderId) return; // already resolved
    const check = () =>
      fetch(`${API}/orders/${order.order_id}/status`)
        .then((r) => r.json())
        .then((s) => {
          if (s.order_status === "paid") setPaidOrderId(order.order_id);
          if (s.order_status === "failed" || s.order_status === "cancelled") setFailedOrderId(order.order_id);
        })
        .catch(() => {}); // a transient miss just retries next tick
    const timer = setInterval(check, 4000);
    return () => clearInterval(timer);
  }, [order, paidOrderId, failedOrderId]);

  // Add the user's message, send it to the agent, then add the reply.
  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: cid, message: text }),
      });
      if (!res.ok) throw new Error("bad status");
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: data.reply }]);
      if (data.products && data.products.length) setProducts(data.products); // keep old cards if none this turn
      if (data.cart && data.cart.items && data.cart.items.length) {
        setCart(data.cart);
        setOrder(null); // a new cart makes any earlier payment link stale
      }
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "⚠️ Couldn't reach the agent. Please try again." }]);
    } finally {
      setBusy(false);
    }
  }

  // The buyer's explicit "Confirm & Pay": turn the current cart into a Razorpay
  // payment link. This is the only action that moves money.
  async function checkout(attemptNum = attempt) {
    if (paying) return;
    setPaying(true);
    setCheckoutError("");
    try {
      const res = await fetch(`${API}/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: cid, email, attempt: attemptNum }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        // Show the server's explainable reason (e.g. a guardrail block), not a generic line.
        setCheckoutError(`⚠️ ${data.detail || "Couldn't start checkout. Please try again."}`);
        return;
      }
      setOrder(data);
    } catch {
      setCheckoutError("⚠️ Couldn't start checkout. Please try again.");
    } finally {
      setPaying(false);
    }
  }

  // Open Razorpay's embedded Checkout popup for an order. The buyer pays without
  // leaving the page; on success Razorpay hands us a signed receipt, which we pass
  // to /payment/verify so the SERVER (not the browser) decides the order is paid.
  // If the checkout script didn't load, fall back to the hosted payment link.
  function openRazorpay(ord) {
    if (!window.Razorpay || !razorpayKey) {
      window.open(ord.payment_link_url, "_blank"); // graceful fallback: the link still works
      return;
    }
    const rzp = new window.Razorpay({
      key: razorpayKey,
      order_id: ord.razorpay_order_id,   // the modal pays against the Razorpay order
      amount: ord.amount,
      currency: "INR",
      name: "CartPilot",
      description: `Order #${ord.order_id}`,
      prefill: { email },
      handler: (resp) => verifyPayment(ord, resp), // Razorpay calls this on success
    });
    rzp.open();
  }

  // Send the modal's signed receipt to the server to verify + mark paid. We trust
  // the server's answer, not the popup: only a genuine signature flips us to paid.
  async function verifyPayment(ord, resp) {
    try {
      const res = await fetch(`${API}/payment/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: ord.order_id,
          razorpay_order_id: resp.razorpay_order_id,
          razorpay_payment_id: resp.razorpay_payment_id,
          razorpay_signature: resp.razorpay_signature,
        }),
      });
      if (res.ok) setPaidOrderId(ord.order_id); // server verified -> flip to the green panel
    } catch {
      // on any failure we stay on "waiting" so the buyer can retry; we never show paid without the server's OK
    }
  }

  // Best-effort: record the buyer's recovery choice (with the options we offered)
  // to the audit trail, so the failure→recovery decision is part of the
  // tamper-evident story. Returns the fetch so a reissue can await it first —
  // that keeps the ledger's hash chain written one entry at a time.
  function logRecovery(choice) {
    return fetch(`${API}/recovery`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: cid, failed_order_id: order?.order_id, choice }),
    }).catch(() => {}); // a failed log must never block the actual recovery
  }

  // Reissue after a failure: log the choice, then bump the attempt so the backend
  // sees a NEW idempotency key and mints a FRESH payment link (instead of
  // returning the failed order). The buyer can then pay this new link and succeed.
  async function retry(choice) {
    await logRecovery(choice);
    const next = attempt + 1;
    setAttempt(next);
    setOrder(null);
    setFailedOrderId(null);
    checkout(next);
  }

  // The current order counts as paid once the live event names its id.
  const paid = order && order.order_id === paidOrderId;
  // ...and failed once a failure event names it, so we can reassure the buyer.
  const failed = order && order.order_id === failedOrderId;

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
      <h1 style={{ marginBottom: 16 }}>CartPilot</h1>

      {/* Merchant metrics: four live KPIs across the top for the judges. */}
      <MetricsStrip metrics={metrics} />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 320 }}>

      {/* Message list */}
      <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12, minHeight: 320, marginBottom: 12 }}>
        {messages.length === 0 && (
          <p style={{ color: "#888" }}>Ask me to find you a phone…</p>
        )}
        {messages.map((m, i) => (
          <p key={i} style={{ textAlign: m.role === "user" ? "right" : "left" }}>
            <span
              style={{
                background: m.role === "user" ? "#dcf8c6" : "#eee",
                padding: "6px 10px",
                borderRadius: 12,
                display: "inline-block",
                whiteSpace: "pre-wrap",
              }}
            >
              {m.text}
            </span>
          </p>
        ))}
        {busy && <p style={{ color: "#888" }}>CartPilot is typing…</p>}
      </div>

      {/* Recommended product cards */}
      {products.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <h3 style={{ margin: "0 0 8px" }}>Recommended</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {products.map((p) => (
              <div key={p.id} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12, width: 170 }}>
                <strong>{p.name}</strong>
                <div style={{ color: "#555", fontSize: 13, margin: "4px 0" }}>{p.specs}</div>
                <div style={{ fontWeight: "bold" }}>{rupees(p.price)}</div>
                {p.reason && <div style={{ color: "#888", fontSize: 12, marginTop: 4 }}>{p.reason}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cart summary */}
      {cart && cart.items && cart.items.length > 0 && (
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <h3 style={{ margin: "0 0 8px" }}>Your cart</h3>
          {/* Items the agent tried to add but couldn't — shown plainly, not silently dropped. */}
          {cart.unavailable && cart.unavailable.length > 0 && (
            <div style={{ background: "#fff5f5", border: "1px solid #ffc9c9", borderRadius: 6, padding: "6px 8px", marginBottom: 8, fontSize: 13, color: "#c92a2a" }}>
              {cart.unavailable.map((u) => (
                <div key={u.product_id}>🚫 {u.name || `Item #${u.product_id}`} — {u.reason}</div>
              ))}
            </div>
          )}
          {cart.items.map((item) => (
            <div key={item.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}>
              <span>{item.name} × {item.quantity}</span>
              <span>{rupees(item.line_total)}</span>
            </div>
          ))}
          <hr style={{ border: "none", borderTop: "1px solid #eee", margin: "8px 0" }} />
          <div style={{ display: "flex", justifyContent: "space-between", fontWeight: "bold" }}>
            <span>Total</span>
            <span>{rupees(cart.total)}</span>
          </div>
          {cart.over_budget && (
            <div style={{ color: "#c00", fontSize: 13, marginTop: 4 }}>
              ⚠️ {rupees(cart.over_by)} over budget
            </div>
          )}

          {/* Checkout — only within budget: an over-budget cart can't be paid (bounded). */}
          {!cart.over_budget && !order && (
            <div style={{ marginTop: 12 }}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email for the receipt"
                style={{ width: "100%", padding: 8, marginBottom: 8, boxSizing: "border-box" }}
              />
              <button
                onClick={() => checkout()}
                disabled={paying}
                style={{ width: "100%", padding: 10, background: "#2b8a3e", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer" }}
              >
                {paying ? "Starting checkout…" : `Confirm & Pay ${rupees(cart.total)}`}
              </button>
              {checkoutError && <div style={{ color: "#c00", fontSize: 13, marginTop: 6 }}>{checkoutError}</div>}
            </div>
          )}

          {/* Order placed. While awaiting payment, an amber panel holds the Razorpay
              link. The instant the verified webhook reports payment, the live SSE
              event flips this panel to a green "order confirmed". */}
          {order && (paid ? (
            <div style={{ marginTop: 12, textAlign: "center", background: "#e6f4ea", border: "1px solid #a3d9b1", borderRadius: 8, padding: 12 }}>
              <div style={{ fontWeight: "bold", color: "#2b8a3e" }}>✅ Payment received — order confirmed</div>
              <div style={{ color: "#888", fontSize: 12, marginTop: 6 }}>Order #{order.order_id} · paid</div>
            </div>
          ) : failed ? (
            <div style={{ marginTop: 12, textAlign: "center", background: "#fff5f5", border: "1px solid #ffc9c9", borderRadius: 8, padding: 12 }}>
              <div style={{ fontWeight: "bold", color: "#c92a2a", marginBottom: 6 }}>⚠️ Payment didn't go through</div>
              <div style={{ color: "#555", fontSize: 14 }}>Don't worry — no money moved, so you haven't been charged. Your cart is safe.</div>
              {/* Recovery options. Retry / switch method reissue a FRESH payment link
                  (a bumped attempt = a new idempotency key, so create_order mints a new
                  link the buyer can actually complete — works even if the old one
                  expired); adjust cart bumps the attempt too, then drops back to the
                  cart to change items before paying again. */}
              <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 10 }}>
                <button onClick={() => retry("retry")}
                   style={{ padding: "6px 12px", background: "#2b8a3e", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>Retry payment</button>
                <button onClick={() => retry("switch_method")}
                   style={{ padding: "6px 12px", background: "#fff", color: "#333", border: "1px solid #ccc", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>Switch method</button>
                <button onClick={() => { logRecovery("adjust_cart"); setOrder(null); setFailedOrderId(null); setAttempt((a) => a + 1); }}
                   style={{ padding: "6px 12px", background: "#fff", color: "#333", border: "1px solid #ccc", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>Adjust cart</button>
              </div>
              <div style={{ color: "#888", fontSize: 12, marginTop: 10 }}>Order #{order.order_id} · payment failed</div>
            </div>
          ) : (
            <div style={{ marginTop: 12, textAlign: "center", background: "#fff8e1", border: "1px solid #ffe08a", borderRadius: 8, padding: 12 }}>
              <div style={{ fontWeight: "bold", color: "#a06000", marginBottom: 8 }}>⏳ Waiting for payment…</div>
              <button
                onClick={() => openRazorpay(order)}
                style={{ display: "block", width: "100%", padding: 10, background: "#2b8a3e", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontWeight: "bold" }}
              >
                Pay {rupees(order.amount)} with Razorpay
              </button>
              <div style={{ color: "#888", fontSize: 12, marginTop: 8 }}>
                Order #{order.order_id} · {order.status} — a secure Razorpay window opens on this page.
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Input box: Enter or the Send button submits the form */}
      <form onSubmit={(e) => { e.preventDefault(); send(); }} style={{ display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          style={{ flex: 1, padding: 8 }}
        />
        <button type="submit" disabled={busy} style={{ padding: "8px 16px" }}>Send</button>
      </form>
      </div>

      {/* Audit side panel: the live, tamper-evident trail judges can watch and export. */}
      <aside style={{ width: 320, border: "1px solid #ddd", borderRadius: 8, padding: 12, maxHeight: "80vh", overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h3 style={{ margin: 0 }}>Audit trail</h3>
          {audit && audit.entries.length > 0 && (
            <a href={`${API}/audit/${cid}/export`} style={{ fontSize: 12 }}>Export</a>
          )}
        </div>
        {audit && audit.entries.length > 0 ? (
          <>
            <div style={{ fontSize: 13, fontWeight: "bold", marginBottom: 8, color: audit.verified ? "#2b8a3e" : "#c00" }}>
              {audit.verified ? "✔ Chain verified" : "✖ Chain broken"}
            </div>
            {audit.entries.map((e) => {
              const ex = explain(e);   // rich four-field card, or null for plain chat lines
              return (
                <div key={e.id} style={{ background: ACTION_COLOR[e.action] || "#f1f3f5", borderRadius: 6, padding: "6px 8px", marginBottom: 6 }}>
                  {ex ? (
                    <>
                      <div style={{ fontSize: 12, fontWeight: "bold" }}>{ex.action}</div>
                      <div style={{ fontSize: 11, color: "#333", marginTop: 2 }}><b>Params:</b> {ex.params}</div>
                      <div style={{ fontSize: 11, color: "#333" }}><b>Why:</b> {ex.rationale}</div>
                      <div style={{ fontSize: 11, color: "#333" }}><b>Impact:</b> {ex.expected_impact}</div>
                    </>
                  ) : (
                    <>
                      <div style={{ fontSize: 12, fontWeight: "bold" }}>{e.action === "buyer_message" ? "Buyer" : e.action === "agent_reply" ? "CartPilot" : e.action}</div>
                      <div style={{ fontSize: 12, color: "#333", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{summarize(e)}</div>
                    </>
                  )}
                  <div style={{ fontSize: 10, color: "#999", fontFamily: "monospace", marginTop: 2 }}>#{e.hash.slice(0, 12)}…</div>
                </div>
              );
            })}
          </>
        ) : (
          <p style={{ color: "#888", fontSize: 13 }}>No activity yet — start chatting.</p>
        )}
      </aside>
      </div>
    </div>
  );
}
