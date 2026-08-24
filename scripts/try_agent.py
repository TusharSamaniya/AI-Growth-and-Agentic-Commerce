# Quick manual test of the agent loop.
# Run from the project root:  python -m scripts.try_agent

import sys

from backend.agent import run_agent

sys.stdout.reconfigure(encoding="utf-8")

# Use a question passed on the command line, else fall back to a default.
question = sys.argv[1] if len(sys.argv) > 1 else "I want a 5G phone under 10000 rupees. What do you suggest?"

messages = [
    {"role": "system", "content": (
        "You are CartPilot, a helpful shopping assistant. Use the tools to search the "
        "catalog before answering. Prices are stored in paise (Rs 1 = 100 paise), so "
        "10000 rupees is 1000000 paise. Show prices to the buyer in rupees."
    )},
    {"role": "user", "content": question},
]

answer = run_agent(messages)
print("\nAgent:", answer)
