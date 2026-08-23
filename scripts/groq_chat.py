# De-risk script: send one chat message to Groq and print the reply.
# Run from the project root:  .venv/Scripts/python -m scripts.groq_chat

from groq import Groq

from backend.config import settings

client = Groq(api_key=settings.groq_api_key)

# messages is a list of turns. "user" is us; the model replies as "assistant".
response = client.chat.completions.create(
    model=settings.groq_model,
    messages=[
        {"role": "user", "content": "In one sentence, what is Razorpay?"},
    ],
)

# The reply text lives at choices[0].message.content.
print("Model:", settings.groq_model)
print("Reply:", response.choices[0].message.content)
