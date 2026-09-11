# AI Placement Assistant

An AI-first placement assistant for college placement cells: RAG over placement documents, a LangGraph agent, MCP tools, eligibility engine, and a full student/admin app.

**Stack:** Next.js + FastAPI + PostgreSQL + Weaviate (vectors) + Redis + Groq (LLM) + LangGraph + MCP

## Build phases

See [Build-Plan.md](./Build-Plan.md). Guiding order: RAG → LLM → Agent → MCP → Agent Tools → AI Evaluation → Backend → Frontend → Advanced Features → Testing → Production.

## Repo layout

```
backend/        FastAPI app (api, core, models, schemas, services, ai) + alembic + tests
mcp-servers/    placement-mcp, student-mcp, knowledge-mcp
frontend/       Next.js app
docs/           architecture, ER model, security model, eval baselines
.github/        CI workflows
```

## Docs

- [Architecture](./docs/architecture.md)
- [ER Model](./docs/er-model.md)
- [Security Model](./docs/security-model.md)

## Setup

```bash
cp .env.example .env   # fill in GROQ_API_KEY etc.

# Start Weaviate (local Docker, both ports required by the v4 client)
docker run -d -p 8080:8080 -p 50051:50051 --name weaviate cr.weaviate.io/semitechnologies/weaviate:latest

# Start PostgreSQL (host port 5433 to avoid clashing with a local Postgres)
docker run -d --name placepilot-postgres -p 5433:5432 \
  -e POSTGRES_USER=placepilot -e POSTGRES_PASSWORD=placepilot -e POSTGRES_DB=placepilot \
  postgres:16-alpine

cd backend
pip install -r requirements.txt
python -m app.db.seed     # creates schema + seeds demo users, companies, drives, applications
python -m app.ai.ingest   # builds sample corpus + DocumentChunk collection, embeds and inserts

# Start the three MCP servers (one-time infra; reuse while they run)
python -m app.mcp.run placement   # http://127.0.0.1:8101/mcp
python -m app.mcp.run student     # http://127.0.0.1:8102/mcp
python -m app.mcp.run knowledge   # http://127.0.0.1:8103/mcp

python -m app.ai.rag_demo     # retrieval + grounded Q&A demo
python -m app.agent.cli_demo  # LangGraph agent via MCP: 4 workflows, authz negative test, persistence
python -m app.eval.runner     # Phase 5 eval suite -> docs/eval-baseline.md
uvicorn app.main:app --reload
```

MCP servers expose JWT-guarded tools (authz re-checked per call, all calls audit-logged to the `audit_log` table). See [MCP demo](./docs/mcp-demo.md).
