# Architecture

## System Flow

```
Student (browser)
    │
    ▼
Next.js / React frontend
    │  HTTP + JWT
    ▼
FastAPI backend  ──────────────►  PostgreSQL (structured data)
    │  │
    │  └──────────────────────►  Redis (sessions / rate limits)
    │
    ▼
AI Gateway (backend/app/ai — LLM service, structured outputs, guardrails)
    │
    ▼
LangGraph Agent
    │  tools
    ├──► RAG retriever ──► Weaviate (vector search over placement docs)
    ├──► MCP servers (placement-mcp / student-mcp / knowledge-mcp)
    │        └── re-check caller identity + role on EVERY tool call
    └──► Groq API (LLM inference: llama-3.3-70b / llama-3.1-8b)
```

## Each arrow, in one sentence

- **Student → Frontend:** the student interacts with a Next.js UI; the browser never talks to the AI stack directly.
- **Frontend → FastAPI:** all requests are HTTPS with a JWT in the `Authorization` header; FastAPI validates and authorizes every request server-side.
- **FastAPI → PostgreSQL:** structured relational data (users, drives, applications, etc.) via SQLAlchemy ORM with parameterized queries only.
- **FastAPI → Redis:** session/conversation state and rate limiting, so agent conversations survive restarts.
- **FastAPI → AI Gateway:** authenticated endpoints (e.g. `POST /ai/chat`) hand off to the LLM/agent layer, passing the verified `student_id` — never trusting client claims.
- **AI Gateway → LangGraph Agent:** the agent graph routes intent → tool selection → tool execution → LLM synthesis; it is the only component that talks to LLMs and tools.
- **Agent → RAG retriever (Weaviate):** policy/document questions are answered by embedding the query, retrieving top-k chunks from Weaviate, and forcing the LLM to cite them; if nothing relevant is retrieved, the system declines instead of hallucinating.
- **Agent → MCP servers:** data-mutating or personal-data tools run in separate MCP servers; each tool independently re-validates caller identity/role before executing.
- **Agent → Groq:** all LLM inference goes through Groq's OpenAI-compatible API; outputs are validated against Pydantic schemas and retried/rejected on malformed output.

## Storage split

| Store | What lives there |
|---|---|
| **PostgreSQL** | Users, student profiles, companies, drives, eligibility rules, applications, status history, notifications, skills (relational only) |
| **Weaviate** | Document chunk text + embeddings as a `DocumentChunk` collection, keyed back to `documents.id` via metadata (the old `document_chunks` Postgres table is gone) |
| **Redis** | Conversation state, rate-limit counters, idempotency keys |

## Key invariants

1. Eligibility is decided only by the deterministic rule engine; the LLM explains, never decides.
2. RAG answers must be grounded and cited, or declined.
3. Every LLM output is schema-validated; malformed output is retried once, then fails loudly.
4. No component trusts the frontend or the LLM for authorization — every API endpoint and MCP tool re-checks identity/role.
