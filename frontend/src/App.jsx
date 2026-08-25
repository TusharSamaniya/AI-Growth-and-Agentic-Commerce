import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [messages, setMessages] = useState([]); // each: { role: "user" | "assistant", text }
  const [input, setInput] = useState("");
  const [cid] = useState(() => crypto.randomUUID()); // one conversation (+ audit trail) per page load
  const [busy, setBusy] = useState(false);          // true while waiting for the agent's reply

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
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "⚠️ Couldn't reach the agent. Please try again." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 600, margin: "0 auto", padding: 24 }}>
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
  );
}
