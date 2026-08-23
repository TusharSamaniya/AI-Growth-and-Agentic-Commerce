# The contract every LLM backend must follow.
# The rest of the app talks to `provider.chat(...)` and never to a specific SDK,
# so we can swap Groq for another model without rewriting the agent.

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """A contract every LLM backend must follow (Groq now, others later)."""

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict] | None = None):
        """Send the conversation (and optional tool schemas) to the model and return its reply."""
