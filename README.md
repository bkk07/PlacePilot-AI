# AI Placement Assistant

An AI-first placement assistant for college placement cells: RAG over placement documents, a LangGraph agent, MCP tools, eligibility engine, and a full student/admin app.

**Stack:** React (Vite) + Tailwind CSS + FastAPI + PostgreSQL + Weaviate (vectors) + Redis + Groq (LLM) + LangGraph + MCP

## Build phases

See [Build-Plan.md](./Build-Plan.md). Guiding order: RAG → LLM → Agent → MCP → Agent Tools → AI Evaluation → Backend → Frontend → Advanced Features → Testing → Production.

## Repo layout

```
backend/        FastAPI app (api, core, models, schemas, services, ai) + alembic + tests
mcp-servers/    placement-mcp, student-mcp, knowledge-mcp
frontend/       React app (Vite + Tailwind CSS)
docs/           architecture, ER model, security model, eval baselines
.github/        CI workflows
```

## Docs

- [Architecture](./docs/architecture.md)
- [ER Model](./docs/er-model.md)
- [Security Model](./docs/security-model.md)
- [MCP Operations Guide](./docs/mcp-ops.md)

## Setup

```bash
cp .env.example .env   # fill in GROQ_API_KEY and a strong JWT_SECRET

# Option A — one command (Postgres, Redis, Weaviate, API, all three MCP servers):
docker compose up -d

# Option B — manual:
docker run -d -p 8080:8080 -p 50051:50051 --name weaviate cr.weaviate.io/semitechnologies/weaviate:latest
docker run -d --name placepilot-postgres -p 5433:5432 \
  -e POSTGRES_USER=placepilot -e POSTGRES_PASSWORD=placepilot -e POSTGRES_DB=placepilot \
  postgres:16-alpine

cd backend
pip install -r requirements.txt
python -m alembic upgrade head   # apply migrations (creates all tables)
python -m app.db.seed     # seeds demo users, companies, drives, applications
python -m app.ai.ingest   # incremental corpus ingest (content-hashed; --rebuild / --prune supported)

# Start the three MCP servers (one-time infra; reuse while they run)
python -m app.mcp.run placement   # http://127.0.0.1:8101/mcp
python -m app.mcp.run student     # http://127.0.0.1:8102/mcp
python -m app.mcp.run knowledge   # http://127.0.0.1:8103/mcp

python -m app.ai.rag_demo     # retrieval + grounded Q&A demo
python -m app.agent.cli_demo  # LangGraph agent via MCP: 4 workflows, authz negative test, persistence
python -m app.eval.runner     # Phase 5 eval suite -> docs/eval-baseline.md
python -m app.eval.runner --set jsonl   # expanded-corpus eval set (data/eval/rag_eval_questions_new.jsonl)
uvicorn app.main:app --reload  # API on http://127.0.0.1:8000 (docs at /docs)
```

Frontend (React + Vite + Tailwind CSS):

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 (proxies /api -> http://127.0.0.1:8000)
npm run build
```

## API

Auth is JWT bearer. Students sign up via `POST /auth/signup` and log in with `POST /auth/login`
(demo: `asha@college.edu` / `student-pass`, admin `placement@college.edu` / `admin-pass`).

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| Student | `GET/PUT /students/me/profile`, `GET /students/me/eligibility/{drive_id}` |
| Drives | `GET /drives` (filter: `query`, `company`, `role`, `status`), `GET /drives/{id}`, `POST /drives` (admin) |
| Companies | `GET /companies/{id}` |
| Applications | `POST /applications`, `GET /applications`, `PATCH /applications/{id}` |
| AI | `POST /ai/chat` (agent reply + citations), `POST /ai/chat/stream` (SSE: intent/tools/reply/citations/done) |
| Knowledge | `POST /knowledge/documents` (admin upload to RAG corpus), `GET /knowledge/documents` (manifest), `DELETE /knowledge/documents/{id}` |

Every endpoint enforces auth + role server-side; applications follow a strict status state machine
(`app/services/application_state.py`) with an append-only history and idempotency keys.

Migrations live in `backend/alembic/` (`python -m alembic upgrade head`).

MCP servers expose JWT-guarded tools (authz re-checked per call, all calls audit-logged to the `audit_log` table). See [MCP demo](./docs/mcp-demo.md).
