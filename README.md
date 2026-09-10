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

cd backend
pip install -r requirements.txt
python -m app.ai.ingest   # builds sample corpus + DocumentChunk collection, embeds and inserts
python -m app.ai.rag_demo  # retrieval + grounded Q&A demo (LLM answers if GROQ_API_KEY set)
python -m app.agent.cli_demo  # LangGraph agent: 4 workflows + conversation persistence
uvicorn app.main:app --reload
```
