# The contract every LLM backend must follow, plus two implementations.
# The rest of the app talks to `provider.chat(...)` and never to a specific SDK,
# so we can swap models by changing one env var (LLM_PROVIDER) — no app rewrite.

import json
from abc import ABC, abstractmethod

from groq import Groq
from openai import OpenAI

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
    """Talks to Groq's chat API using the groq SDK."""

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        options = {"model": self.model, "messages": messages}
        if tools:
            options["tools"] = tools
        message = self.client.chat.completions.create(**options).choices[0].message
        return _normalize(message)


class HostedProvider(LLMProvider):
    """Any hosted, OpenAI-compatible model via the openai SDK.

    The demo points at Groq's OpenAI-compatible endpoint so it works with the key
    you already have. Swap base_url/api_key/model to use OpenAI, Together, etc.
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = settings.groq_model

    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        options = {"model": self.model, "messages": messages}
        if tools:
            options["tools"] = tools
        message = self.client.chat.completions.create(**options).choices[0].message
        return _normalize(message)


def get_provider() -> LLMProvider:
    """Pick the provider from LLM_PROVIDER ('groq' or 'hosted'); defaults to groq."""
    if settings.llm_provider == "hosted":
        return HostedProvider()
    return GroqProvider()
