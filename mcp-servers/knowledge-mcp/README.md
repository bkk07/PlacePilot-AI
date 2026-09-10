# knowledge-mcp

Served from `backend/app/mcp/servers.py` — run with `python -m app.mcp.run knowledge` (port 8103).

Tools: `search_policy_docs` (RAG over the Weaviate `DocumentChunk` collection).

Answers must be grounded in retrieved chunks and cited, or declined — the agent never answers policy
questions from model memory.