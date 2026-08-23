# Quick manual test of the GroqProvider wrapper.
# Run from the project root:  python -m scripts.try_groq_provider

from backend.llm import GroqProvider

provider = GroqProvider()

reply = provider.chat([{"role": "user", "content": "Say hello in exactly 5 words."}])

print("Normalized reply:", reply)      # a plain dict, not a Groq object
print("Text:", reply["text"])
print("Tool calls:", reply["tool_calls"])  # empty list here — we sent no tools
