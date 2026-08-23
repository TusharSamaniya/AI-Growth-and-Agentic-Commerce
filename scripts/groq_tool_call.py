# De-risk script: let the model call a fake `get_time` tool, then answer using the result.
# Run from the project root:  .venv/Scripts/python -m scripts.groq_tool_call

from datetime import datetime

from groq import Groq

from backend.config import settings

client = Groq(api_key=settings.groq_api_key)


# 1. The real Python function the model is allowed to ask for.
def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 2. Describe that function to the model so it knows the tool exists.
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current date and time.",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]

# 3. The running conversation. We start with the user's question.
messages = [{"role": "user", "content": "What time is it right now?"}]

# 4. First call: the model chooses to REQUEST the tool instead of answering.
first = client.chat.completions.create(
    model=settings.groq_model, messages=messages, tools=tools
)
reply = first.choices[0].message
messages.append(reply)  # remember what the model asked for

# 5. Run each requested tool and send its result back as a "tool" message.
for call in reply.tool_calls:
    result = get_time()
    print("Model called:", call.function.name, "-> got:", result)
    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

# 6. Second call: the model writes its final answer using the tool result.
second = client.chat.completions.create(model=settings.groq_model, messages=messages)
print("Final answer:", second.choices[0].message.content)
