# Automated test for the /chat endpoint.
# NOTE: test_chat_replies calls the REAL Groq API, so it needs internet + a valid key.
# Run from the project root:  python -m pytest

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_chat_replies():
    response = client.post("/chat", json={"message": "Say hi in 5 words."})
    assert response.status_code == 200
    body = response.json()
    # The model's exact words vary, so we check the shape, not the text.
    assert isinstance(body["text"], str) and body["text"] != ""
    assert isinstance(body["tool_calls"], list)


def test_chat_requires_message():
    # Missing "message" is rejected before we ever call Groq.
    response = client.post("/chat", json={})
    assert response.status_code == 422
