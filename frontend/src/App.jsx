import { useEffect, useState } from "react";

// Where the FastAPI backend runs (uvicorn backend.main:app --port 8000).
// The backend's CORS settings allow this dev app to call it from the browser.
const API = "http://127.0.0.1:8000";

export default function App() {
  const [status, setStatus] = useState("checking...");

  // On first render, ask the backend if it's alive and show the answer.
  // This proves the frontend can reach the backend.
  useEffect(() => {
    fetch(`${API}/health`)
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("backend not reachable"));
  }, []);

  return (
    <div style={{ fontFamily: "sans-serif", padding: 24 }}>
      <h1>CartPilot</h1>
      <p>Backend health: {status}</p>
    </div>
  );
}
