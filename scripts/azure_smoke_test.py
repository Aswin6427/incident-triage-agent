"""
Azure OpenAI smoke test — verifies the migration works end-to-end against
real Azure OpenAI: one chat completion + one embedding call.

Run:  PYTHONPATH=. python scripts/azure_smoke_test.py
Auth: requires AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and the chat /
      embedding deployment names set in .env (or env).
"""
from backend.config import get_settings

settings = get_settings()
print(f"Endpoint   : {settings.azure_openai_endpoint or '(unset!)'}")
print(f"API version: {settings.azure_openai_api_version}")
print(f"Chat       : {settings.azure_openai_chat_deployment}")
print(f"Embed      : {settings.azure_openai_embedding_deployment}")
print("-" * 50)

# ── 1. Chat completion ───────────────────────────────────────
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.messages import HumanMessage

llm = AzureChatOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version,
    azure_deployment=settings.azure_openai_chat_deployment,
    temperature=0,
    max_tokens=50,
)
resp = llm.invoke([HumanMessage(content="Reply with exactly: AZURE_CHAT_OK")])
print(f"[chat]  response: {resp.content!r}")

# ── 2. Embedding ─────────────────────────────────────────────
emb = AzureOpenAIEmbeddings(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version,
    azure_deployment=settings.azure_openai_embedding_deployment,
)
vec = emb.embed_query("incident triage smoke test")
print(f"[embed] dimension: {len(vec)}  first3: {[round(x, 4) for x in vec[:3]]}")

print("-" * 50)
print("[OK] Azure OpenAI is working (chat + embeddings).")
