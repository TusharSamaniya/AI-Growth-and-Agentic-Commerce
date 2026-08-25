# Automated test for the /chat endpoint.
# NOTE: test_chat_replies calls the REAL Groq API, so it needs internet + a valid key.
# Run from the project root:  python -m pytest

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_chat_replies():
    response = client.post("/chat", json={"conversation_id": "test-1", "message": "Say hi in 5 words."})
    assert response.status_code == 200
    body = response.json()
    # The model's exact words vary, so we check the shape, not the text.
    assert isinstance(body["reply"], str) and body["reply"] != ""


def test_chat_requires_message():
    # A missing field (conversation_id or message) is rejected before we call Groq.
    response = client.post("/chat", json={})
    assert response.status_code == 422
