# The contract every LLM backend must follow, plus the Groq implementation.
# The rest of the app talks to `provider.chat(...)` and never to a specific SDK,
# so we can swap Groq for another model without rewriting the agent.

import json
from abc import ABC, abstractmethod

from groq import Groq

from backend.config import settings


class LLMProvider(ABC):
    """A contract every LLM backend must follow (Groq now, others later)."""

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """Send the conversation (and optional tool schemas) to the model and return its reply."""


def _normalize(message):
    """Turn a provider's raw reply into a plain, provider-independent dict."""
    return {
        "text": message.content,
        "tool_calls": [
            {"id": c.id, "name": c.function.name, "arguments": json.loads(c.function.arguments)}
            for c in (message.tool_calls or [])
        ],
    }


class GroqProvider(LLMProvider):
    """Talks to Groq's OpenAI-compatible chat API."""

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        # Only pass `tools` when we actually have some (plain /chat calls with none).
        options = {"model": self.model, "messages": messages}
        if tools:
            options["tools"] = tools
        message = self.client.chat.completions.create(**options).choices[0].message
        return _normalize(message)
