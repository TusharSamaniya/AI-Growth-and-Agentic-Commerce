import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

// Format a paise integer as rupees, e.g. 899900 -> "₹8,999".
const rupees = (paise) => `₹${(paise / 100).toLocaleString("en-IN")}`;

// A light background per audit action, so judges can scan the trail by type.
const ACTION_COLOR = {
  buyer_message: "#e7f1ff",
  agent_decision: "#efe7ff",
  agent_reply: "#e9ecef",
  order_created: "#fff3cd",
  status_change: "#e6f4ea",
};

// A short, human-readable line for one audit entry, based on its action + data.
function summarize(entry) {
  const d = entry.data || {};
  switch (entry.action) {
    case "buyer_message": return d.text;
    case "agent_reply": return d.text;
    case "agent_decision": return `tool: ${d.tool}`;
    case "order_created": return `order #${d.order_id} · ${rupees(d.amount)} · ${d.status}`;
    case "status_change": return `${d.from} → ${d.to}`;
    default: return JSON.stringify(d);
  }
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
  const [checkoutError, setCheckoutError] = useState(""); // a calm message if checkout fails
  const [paidOrderId, setPaidOrderId] = useState(null);   // which order the live event told us is paid
  const [audit, setAudit] = useState(null);               // this conversation's audit trail (polled live)

  // Subscribe to the server's live event stream. When the payment webhook fires,
  // the backend publishes a "payment_received" event and it arrives here instantly
  // (no polling). We just note which order was paid; the render flips to green.
  useEffect(() => {
    const es = new EventSource(`${API}/events`);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "payment_received") setPaidOrderId(data.order_id);
      } catch {
        // ignore keepalives and any non-JSON frames
      }
    };
    return () => es.close(); // close the stream when the page goes away
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
  async function checkout() {
    if (paying) return;
    setPaying(true);
    setCheckoutError("");
    try {
      const res = await fetch(`${API}/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: cid, email }),
      });
      if (!res.ok) throw new Error("bad status");
      setOrder(await res.json());
    } catch {
      setCheckoutError("⚠️ Couldn't start checkout. Please try again.");
    } finally {
      setPaying(false);
    }
  }

  // The current order counts as paid once the live event names its id.
  const paid = order && order.order_id === paidOrderId;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 24, maxWidth: 1000, margin: "0 auto", padding: 24, fontFamily: "sans-serif", alignItems: "flex-start" }}>
      <div style={{ flex: 1, minWidth: 320 }}>
        <h1>CartPilot</h1>

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
                onClick={checkout}
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
          ) : (
            <div style={{ marginTop: 12, textAlign: "center", background: "#fff8e1", border: "1px solid #ffe08a", borderRadius: 8, padding: 12 }}>
              <div style={{ fontWeight: "bold", color: "#a06000", marginBottom: 8 }}>⏳ Waiting for payment…</div>
              <a
                href={order.payment_link_url}
                target="_blank"
                rel="noreferrer"
                style={{ display: "block", padding: 10, background: "#2b8a3e", color: "#fff", borderRadius: 8, textDecoration: "none", fontWeight: "bold" }}
              >
                Pay {rupees(order.amount)} with Razorpay →
              </a>
              <div style={{ color: "#888", fontSize: 12, marginTop: 8 }}>
                Order #{order.order_id} · {order.status} — finish paying in the Razorpay window.
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
            {audit.entries.map((e) => (
              <div key={e.id} style={{ background: ACTION_COLOR[e.action] || "#f1f3f5", borderRadius: 6, padding: "6px 8px", marginBottom: 6 }}>
                <div style={{ fontSize: 12, fontWeight: "bold" }}>{e.action}</div>
                <div style={{ fontSize: 12, color: "#333", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{summarize(e)}</div>
                <div style={{ fontSize: 10, color: "#999", fontFamily: "monospace" }}>#{e.hash.slice(0, 12)}…</div>
              </div>
            ))}
          </>
        ) : (
          <p style={{ color: "#888", fontSize: 13 }}>No activity yet — start chatting.</p>
        )}
      </aside>
    </div>
  );
}
