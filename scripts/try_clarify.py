# Demonstrates clarifying questions: a vague request -> the agent asks first,
# then recommends once the buyer answers (memory carries the answer forward).
# Run from the project root:  python -m scripts.try_clarify

import sys

from backend.agent import chat

sys.stdout.reconfigure(encoding="utf-8")

cid = "clarify-1"  # same id both turns => the answer is remembered

q1 = "I want a good phone."  # vague -> agent should ask before recommending
print("You:", q1)
print("Bot:", chat(cid, q1))

q2 = "My budget is 10000 rupees and I care most about battery life."
print("\nYou:", q2)
print("Bot:", chat(cid, q2))
