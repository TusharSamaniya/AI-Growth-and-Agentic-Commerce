# Demonstrates conversation memory: turn 2 refers back to turn 1 ("one" = the
# phone suggested in turn 1). Only works because we keep the message history.
# Run from the project root:  python -m scripts.try_memory

import sys

from backend.agent import chat

sys.stdout.reconfigure(encoding="utf-8")

cid = "demo-1"  # same id for both turns => same conversation

q1 = "I want a 5G phone under 10000 rupees. What do you suggest?"
print("You:", q1)
print("Bot:", chat(cid, q1))

q2 = "Great, add one to my cart."  # no product named -> needs memory of turn 1
print("\nYou:", q2)
print("Bot:", chat(cid, q2))
