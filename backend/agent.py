# The agent loop: give the model our tools, run whichever it picks, feed the
# result back, and repeat until it has a final answer.
# The tool-call round-trip was first proven in scripts/groq_tool_call.py.

import json

from backend.audit import record
from backend.llm import get_provider
from backend.tools import build_cart, recommend, search_catalog, suggest_addons

# Map each tool name to the real Python function that runs it.
TOOLS = {
    "search_catalog": search_catalog,
    "recommend": recommend,
    "build_cart": build_cart,
    "suggest_addons": suggest_addons,
}

# Describe the tools to the model so it knows what it can call and with what args.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the product catalog. Prices are in paise (Rs 1 = 100 paise).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Words to match in name/specs/brand"},
                    "max_price": {"type": "integer", "description": "Highest price, in paise"},
                    "filters": {"type": "object", "description": 'Exact filters. Valid categories: "phone", "case", "screen_guard". Example: {"category": "phone"}'},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend",
            "description": "Rank a list of products by a preference; returns the best few with reasons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "products": {"type": "array", "items": {"type": "object"},
                                 "description": "Products to rank (from search_catalog)"},
                    "preferences": {"type": "string", "description": "What the buyer wants, e.g. '5G big battery'"},
                },
                "required": ["products"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_cart",
            "description": "Build a cart from product ids (repeat an id for quantity > 1). Total is in paise. Pass budget (paise) to flag an over-budget total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {"type": "array", "items": {"type": "integer"},
                                    "description": "The chosen product ids"},
                    "budget": {"type": "integer", "description": "The buyer's budget in paise, if known"},
                },
                "required": ["product_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_addons",
            "description": "Suggest in-stock accessories that fit the remaining budget. total and budget are in paise.",
            "parameters": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer", "description": "Current cart total, in paise"},
                    "budget": {"type": "integer", "description": "The buyer's budget, in paise"},
                },
                "required": ["total", "budget"],
            },
        },
    },
]

# The agent's standing rules — applied on every turn (persona + the judging-bar rules).
SYSTEM_PROMPT = """You are CartPilot, a friendly shopping assistant for an online phone store.

Always use the tools to look up real products before you answer — never invent products or prices.

Rules you must always follow:
1. Stay within budget: never recommend or add an item priced above the buyer's stated budget.
2. Require confirmation: after building a cart, show it and ask the buyer to confirm before any checkout — never treat a cart as a paid order.
3. Always explain: give a short reason for every product you recommend.
4. Offer choices: when the buyer is still deciding, present 2-3 options with one short pro and one short con each (based on their real specs and price), then ask which they prefer. Skip this only if they already named a specific product.
5. Ask before guessing: if key details are missing (budget, whether they prefer things like camera vs battery, or a brand), ask 1-2 short clarifying questions first, then recommend. Never ask more than two, and don't re-ask what they already told you.
6. Bounded upsell: once the buyer has picked a phone and you know their budget, call suggest_addons(total, budget) and offer only the accessories it returns — they already fit the remaining budget. Never suggest an add-on that would push the total over budget; if nothing fits, don't push accessories.
7. Never hide a breach: whenever you build a cart and know the budget, pass it to build_cart. If the result comes back over_budget, tell the buyer plainly that the cart is over budget and by how much (over_by), and ask how they want to proceed — never present an over-budget cart as if it were fine.

Prices are stored in paise (Rs 1 = 100 paise), so a 10000 rupee budget means 1000000 paise. Always show prices to the buyer in rupees."""


def run_agent(messages: list[dict], max_steps: int = 8, conversation_id: str | None = None) -> str:
    """Let the model call tools until it produces a final answer (bounded by max_steps).

    If conversation_id is given, each tool the model picks is logged to the audit
    trail as an "agent_decision" — the record of what the agent chose to do.
    """
    provider = get_provider()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for _ in range(max_steps):
        reply = provider.chat(messages, tools=TOOL_SCHEMAS)

        # No tool calls -> the model has its final answer.
        if not reply["tool_calls"]:
            return reply["text"]

        # Record the model's tool-call turn (rebuilt in the standard format).
        messages.append({
            "role": "assistant",
            "content": reply["text"],
            "tool_calls": [
                {"id": c["id"], "type": "function",
                 "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                for c in reply["tool_calls"]
            ],
        })

        # Run each tool the model picked and feed the result back.
        for c in reply["tool_calls"]:
            print(f"  [agent] calling {c['name']}({c['arguments']})")
            if conversation_id:
                record(conversation_id, "agent_decision", {"tool": c["name"], "arguments": c["arguments"]})
            function = TOOLS.get(c["name"])
            if function is None:
                result = {"error": f"unknown tool: {c['name']}"}
            else:
                try:
                    result = function(**c["arguments"])
                except Exception as e:  # bad args or tool failure -> tell the model
                    result = {"error": str(e)}
            messages.append({
                "role": "tool",
                "tool_call_id": c["id"],
                "content": json.dumps(result),
            })

    return "Sorry, I couldn't finish that request."


# --- Conversation memory -----------------------------------------------------
# Remember each conversation's messages, keyed by a conversation id, so follow-up
# turns ("add it to my cart") can see what came before.
# In-memory on purpose: this resets when the server restarts, which is fine here.
_conversations: dict[str, list[dict]] = {}


def chat(conversation_id: str, message: str) -> str:
    """Run one conversational turn, remembering the earlier messages."""
    record(conversation_id, "buyer_message", {"text": message})
    history = _conversations.setdefault(conversation_id, [])
    history.append({"role": "user", "content": message})
    reply = run_agent(history, conversation_id=conversation_id)
    history.append({"role": "assistant", "content": reply})
    record(conversation_id, "agent_reply", {"text": reply})
    return reply
