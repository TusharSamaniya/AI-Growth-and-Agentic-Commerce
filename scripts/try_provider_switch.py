# Shows which provider get_provider() picks (set by LLM_PROVIDER) and calls it once.
# Run from the project root:            python -m scripts.try_provider_switch
# Switch to hosted (PowerShell):        $env:LLM_PROVIDER="hosted"; python -m scripts.try_provider_switch
# (Reset it back with:                  $env:LLM_PROVIDER="groq"      )

from backend.config import settings
from backend.llm import get_provider

provider = get_provider()
print("LLM_PROVIDER =", settings.llm_provider, "->", type(provider).__name__)

reply = provider.chat([{"role": "user", "content": "Say hi in 5 words."}])
print("Reply:", reply["text"])
