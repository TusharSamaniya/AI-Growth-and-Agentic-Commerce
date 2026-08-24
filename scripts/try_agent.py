# Quick manual test of the agent loop.
# Run from the project root:  python -m scripts.try_agent

import sys

from backend.agent import run_agent

sys.stdout.reconfigure(encoding="utf-8")

# Use a question passed on the command line, else fall back to a default.
question = sys.argv[1] if len(sys.argv) > 1 else "I want a 5G phone under 10000 rupees. What do you suggest?"

# run_agent supplies the system prompt itself, so we just send the buyer's question.
messages = [{"role": "user", "content": question}]

answer = run_agent(messages)
print("\nAgent:", answer)
