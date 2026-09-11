# AI Placement Assistant — End-to-End Build Plan (Phase by Phase)

**Guiding order (AI-first):** RAG → LLM → Agent → MCP → Agent Tools → AI Evaluation → Backend → Frontend → Advanced Features → Testing → Production

**MVP reminder:** Don't build all 19 features up front. The MVP is: student profile, placement drives, eligibility engine, RAG over placement documents, LLM, LangGraph agent, MCP tools, AI chat, "my eligible drives," and basic application tracking. Phases 0–7 deliver that MVP; Phase 8 expands to the full 19-feature set.

**Relative effort per phase** (so you can plan your own pace — not fixed dates): Phase 0 – S · Phase 1 – M · Phase 2 – S · Phase 3 – M · Phase 4 – M · Phase 5 – S · Phase 6 – L · Phase 7 – L · Phase 8 – L · Phase 9 – M · Phase 10 – M

> **Tech stack update:** Vector database is now **Weaviate** (was pgvector), and LLM calls go through the **Groq API** (was a generic "LLM API"). PostgreSQL stays for structured relational data — it's just no longer doing double duty as a vector store. Details below in Phase 0/1/2.

---

## Roles & Guardrails (Cross-Cutting — touches every phase)

These aren't a phase by themselves. They're decided in Phase 0, implemented across Phases 4/6, and verified in Phases 5/9.

### Roles

| Role | Permissions | Enforced at |
|---|---|---|
| **Student** | View drives, view companies, check eligibility, apply, track/withdraw applications, view recommendations, ask AI assistant, view own profile/history only | API layer (Phase 6) + MCP tool layer (Phase 4) |
| **Placement Admin** | Create/update drives, upload documents, manage companies, update application statuses, manage policies, view analytics | API layer (Phase 6) + MCP tool layer (Phase 4) |
| **Alumni** *(future, not MVP)* | Submit interview experiences, limited read access | Deferred — design the schema now, don't build the flow yet |

Rule: a role is never trusted from the frontend or from the LLM's interpretation of a request — every API endpoint and every MCP tool independently re-checks the caller's identity and role before doing anything.

### Guardrails

**1. AI / LLM guardrails**
- Eligibility is decided only by the deterministic rule engine — the LLM explains the result, never determines it (Phase 6)
- RAG answers must be grounded and cited; if no relevant chunk is retrieved, the system says so instead of answering from the model's general knowledge (Phase 1)
- Every LLM call's output is validated against a structured schema; malformed output is rejected/retried, never passed downstream as-is (Phase 2)
- No invented company-specific facts (selection rounds, CTC, process) unless sourced from an ingested document (Phase 1/8)
- User input is never treated as a system instruction — agent tools validate and sanitize inputs before execution (Phase 3/4)
- Rate limits and cost/token caps on LLM and embedding calls — watch Groq's developer-tier rate limits (TPM/RPM) specifically, since they're generous but not unlimited (Phase 10)

**2. Authorization guardrails**
- Every API endpoint enforces authentication + role check server-side (Phase 6)
- Every MCP tool re-validates caller identity/role before executing — a student's token can never fetch another student's profile, applications, or status (Phase 4)
- Admin-only actions are blocked for the student role at both the API and MCP layers (Phase 4/6)
- Audit logging on sensitive tool and API calls (Phase 4/10)

**3. Data & input guardrails**
- Input validation (Pydantic schemas) on every API and MCP tool input (Phase 2/6)
- ORM/parameterized queries only — no raw string-built SQL (Phase 6)
- Upload validation (file type, size) for document ingestion (Phase 1/6)
- AI responses are checked to never leak another student's PII (Phase 4, verified in Phase 5's eval set)

**4. Business-logic guardrails**
- Idempotency keys on application submission and notification dispatch, so retries never create duplicates (Phase 6/8)
- The eligibility engine is the single source of truth; the eval suite specifically checks the LLM's explanation never contradicts the engine's actual decision (Phase 5/9)
- Application status changes follow a strict state machine (Not Applied → Applied → Shortlisted → … → Selected/Rejected, plus Withdraw) — no arbitrary transitions (Phase 6)

**5. Reliability guardrails**
- Timeouts + retries on all LLM/embedding calls, with a graceful fallback (e.g., show raw drive data if the AI layer is down) (Phase 2/10)
- RAG retrieval failures degrade gracefully rather than blocking chat entirely (Phase 1/10)
- MCP tool failures return a partial answer instead of crashing the agent run (Phase 4)

---

## Phase 0 — Architecture & Foundations  *(effort: S)*

**Goal:** Lock every structural decision before writing feature code.

**Step-by-step:**
1. Write a one-page architecture doc with the flow: Student → React (Vite + Tailwind) → FastAPI → AI Gateway → LangGraph Agent (calling **Groq** for LLM inference) → (RAG via **Weaviate** / MCP / DB Tools) → (**Weaviate** for vectors, **PostgreSQL** for structured data). Explain each arrow in a sentence.
2. Decide the repo layout, e.g.:
   ```
   ai-placement-assistant/
   ├── backend/
   │   ├── app/
   │   │   ├── api/        # routers
   │   │   ├── core/       # config, security
   │   │   ├── models/     # SQLAlchemy models (relational data only)
   │   │   ├── schemas/    # Pydantic schemas
   │   │   ├── services/   # eligibility engine, recommendation engine
   │   │   ├── ai/         # Groq LLM service, Weaviate RAG client, agent
   │   │   └── main.py
   │   ├── alembic/        # migrations
   │   └── tests/
   ├── mcp-servers/
   │   ├── placement-mcp/
   │   ├── student-mcp/
   │   └── knowledge-mcp/
   ├── frontend/            # React app (Vite + Tailwind CSS)
   ├── docs/
   └── .github/workflows/
   ```
3. Design the ER model for the **relational** entities in PostgreSQL: `users`, `student_profiles`, `companies`, `drives`, `drive_eligibility_rules`, `applications`, `application_status_history`, `placement_statistics`, `interview_experiences`, `documents` (metadata only — title, company, type, uploaded_by, uploaded_at), `notifications`, `notification_preferences`, `skills`, `student_skills`, `drive_skills` — PK/FK relationships on paper or dbdiagram.io. Note: the old `document_chunks` table is **gone from Postgres** — chunk text + embeddings now live in Weaviate as a collection, keyed back to `documents.id` via a metadata field.
4. Write the security model doc: two roles (student, admin), auth mechanism (JWT), and the rule that every MCP tool re-checks authorization independently.
5. Create `.env.example` with the variables you now know you need: `DATABASE_URL`, `REDIS_URL`, `WEAVIATE_URL` (defaults to `http://localhost:8080` for the local Docker instance), `GROQ_API_KEY`, `JWT_SECRET`.
6. `git init`, push the skeleton, set up `main` branch protection if you want CI gates later.

**Deliverables:** Architecture doc, ER diagram, repo skeleton on GitHub, `.env.example`
**Exit criteria:** You can explain, without hand-waving, how one request flows from the browser to the database and back.

---

## Phase 1 — RAG (now on Weaviate)  *(effort: M)*

**Goal:** Ground the system in real placement documents before any agent logic touches them.

**Step-by-step:**
1. Run Weaviate locally via Docker — the image needs **both** the HTTP port and the gRPC port mapped (the v4 client uses gRPC under the hood):
   ```
   docker run -d -p 8080:8080 -p 50051:50051 \
     --name weaviate cr.weaviate.io/semitechnologies/weaviate:latest
   ```
   This is the only Weaviate deployment this project uses — local Docker, dev through production, no cloud cluster to provision.
2. `pip install -U weaviate-client` (this is the v4 client — the API is collections-based, not the old v3 schema/class API). Connect with `weaviate.connect_to_local()` — that's the only connection method you need anywhere in the codebase.
3. Write `document_loader.py` and load a small sample set (1 placement policy PDF, 2–3 company JDs, 2–3 interview experience write-ups).
4. Write text extraction + cleaning (strip headers/footers, normalize whitespace).
5. Write the chunker; attach metadata to every chunk: `document_id`, `company`, `year`, `document_type`, `role`, `source`, `page_number`.
6. **Embeddings:** Groq doesn't serve an embeddings endpoint, so use a separate, free/local embedding model — `sentence-transformers` with something like `all-MiniLM-L6-v2` or `BAAI/bge-small-en-v1.5` works well and keeps the whole pipeline cost-free outside of Groq's LLM calls. Create a Weaviate collection (e.g. `DocumentChunk`) with `vector_config=Configure.Vectors.self_provided()` (since you're bringing your own vectors instead of a built-in vectorizer module), and insert each chunk's text + metadata as properties with its embedding passed as `vector=`.
7. Write `retriever.py`: embed the query with the *same* embedding model, then run `collection.query.near_vector(...)` (or `.hybrid(...)` if you want to combine keyword + vector search) against Weaviate, returning top-k chunks with metadata.
8. Write a grounded-answer function: retrieved chunks → prompt template → **Groq** LLM call → answer with inline citations.
9. Manually test 5–10 questions against the sample docs. Confirm citations point to the right source, and out-of-corpus questions get declined rather than hallucinated.

**Deliverables:** Ingestion script, populated Weaviate collection, retriever module, demo Q&A showing grounded/cited answers
**Exit criteria:** Correct chunks retrieved + cited for in-corpus questions; out-of-corpus questions correctly declined.

---

## Phase 2 — LLM (now on Groq)  *(effort: S)*

**Goal:** A reliable LLM layer the rest of the system can call without worrying about raw model quirks.

**Step-by-step:**
1. `pip install groq` (official SDK), or use `langchain-groq`'s `ChatGroq` class if you want it to plug directly into LangGraph nodes — either way it's driven by `GROQ_API_KEY`. Groq's API is OpenAI-compatible at `https://api.groq.com/openai/v1`, so anything built against the OpenAI SDK also works by just swapping the `base_url`.
2. Pick a model per use case rather than one model for everything — check `console.groq.com/docs/models` for the current list/pricing since it changes, but as of now: `llama-3.3-70b-versatile` or `openai/gpt-oss-120b` for reasoning-heavy calls (eligibility explanations, policy Q&A, recommendation reasoning); `llama-3.1-8b-instant` or `openai/gpt-oss-20b` for lightweight/low-latency calls where you don't need the biggest model.
3. Wrap the client in `ai/llm_service.py` (model config, retry/timeout wrapper).
4. Define Pydantic schemas for every structured output you'll need: `EligibilityExplanation`, `RecommendationExplanation`, `PolicyAnswer` (with a citations field), `ChatResponse`.
5. Write one prompt template per use case (eligibility explanation, policy Q&A, recommendation explanation, general chat) as separate functions — not one giant prompt.
6. Wire structured-output parsing — Groq supports JSON-mode structured outputs and tool/function calling (useful later for the agent), so lean on that instead of hand-parsing free text.
7. On parse failure: retry once with a corrective prompt, then fail loudly — never silently pass raw text through as if it were structured.
8. Write unit tests for both the happy path and the malformed-output path.

**Deliverables:** LLM service module (Groq-backed), structured-output schemas, unit tests
**Exit criteria:** LLM calls reliably return validated structured data; failures are caught, not silently swallowed. (Bonus: Groq's inference speed means you should see noticeably fast responses here — worth noting for your eval latency numbers in Phase 5.)

---

## Phase 3 — Agent (LangGraph)  *(effort: M)*

**Goal:** Give the system the ability to understand intent and pick the right tool, before wiring it to real data.

**Step-by-step:**
1. Define the agent's state object (conversation history, retrieved context, tool results, `student_id`).
2. Implement the five MVP tools as plain Python functions first (not MCP yet): `search_drives()`, `get_drive_details()`, `get_student_profile()`, `check_eligibility()`, `get_application_status()` — backed by mock/seeded data if the DB isn't ready.
3. Build the LangGraph graph: intent node → tool-selection node → tool-execution node → LLM-synthesis node (using the Phase 2 **Groq**-backed LLM service) → end.
4. Wire the Phase 1 Weaviate retriever in as one of the tools the agent can pick (for policy questions).
5. Add conversation-state persistence across turns (in-memory dict, or Redis-backed if you want it to survive restarts).
6. Run the four example workflows by hand — eligibility check, policy question, cross-company query, recommendation — and fix routing until all four pick the right tool.

**Deliverables:** Working LangGraph agent, demoable via CLI or a minimal API
**Exit criteria:** All four example workflows produce correct tool selection and a sensible final answer.

---

## Phase 4 — MCP  *(effort: M)*

**Goal:** Replace local function stubs with real, permission-checked tool servers.

**Step-by-step:**
1. Scaffold three MCP servers: `placement-mcp`, `student-mcp`, `knowledge-mcp`, each exposing the tools from the spec.
2. Move the tool logic from Phase 3's local functions into the matching MCP server, now backed by the real database (PostgreSQL for structured lookups, Weaviate for the knowledge server's RAG-backed tools) instead of mocks.
3. Add an authorization check inside every MCP tool handler: extract the caller's `student_id`/role from the auth context, reject any request for another student's data.
4. Add input validation (Pydantic) on every MCP tool's parameters.
5. Add audit logging: every tool call logs who called it, with what params, and the result status.
6. Update the LangGraph agent to call these MCP servers instead of local functions.
7. Write a negative test: student A calling `get_student_profile` with student B's id must fail.

**Deliverables:** Three running MCP servers, agent calling them end-to-end, a passing authz negative test
**Exit criteria:** Phase 3's workflows now run through MCP; unauthorized access attempts are blocked.

---

## Phase 5 — AI Evaluation  *(effort: S)*

**Goal:** A repeatable way to measure RAG + agent quality before building the rest of the app on top of it.

**Step-by-step:**
1. Write 20–30 evaluation questions covering every question type in the spec (stipend lookup, eligible branches, "am I eligible," "why not eligible," cross-company CTC, policy questions).
2. Record the expected answer/expected source chunk for each.
3. Write an eval runner that sends each question through the full agent pipeline and scores: correctness, groundedness, retrieval recall, citation accuracy, hallucination rate, latency, token usage/cost (Groq's per-model pricing makes this easy to compute — cheap models are fractions of a cent per 1K tokens).
4. Run it once, save the baseline numbers in `docs/eval-baseline.md`.
5. Re-run after any prompt/retrieval/model change and diff against the baseline.

**Deliverables:** Eval dataset file, eval runner, baseline metrics report
**Exit criteria:** You can re-run the eval after a change and see, with numbers, whether quality improved or regressed.

---

## Phase 6 — Backend Application  *(effort: L)*

**Goal:** Build the deterministic backbone and connect the AI stack to it.

**Step-by-step:**
1. Finalize the FastAPI project structure (`app/api`, `app/core`, `app/models`, `app/schemas`, `app/services`) from Phase 0.
2. Write SQLAlchemy models for the relational entities (no vector columns needed now — that's all in Weaviate); generate and run the Alembic migration against PostgreSQL.
3. Build auth: signup/login, password hashing, JWT issuance, a `role` field on `users`.
4. Build the eligibility engine as a pure function/service — student profile + drive rules in, eligible/not-eligible + reasons out. Unit test heavily; this is graded logic, not AI.
5. Build Drive APIs: `GET /drives` (search/filter), `GET /drives/{id}`.
6. Build Application APIs: `POST /applications`, `GET /applications`, `PATCH /applications/{id}`.
7. Build Company APIs: `GET /companies/{id}`.
8. Build `POST /ai/chat` — authenticate the user, then hand off to the Phase 3/4 agent (Groq + Weaviate under the hood), passing `student_id` so MCP tools can enforce authorization.
9. Add validation/error handling to every endpoint.

**Deliverables:** Running FastAPI backend with real DB-backed CRUD, tested eligibility engine, working AI chat endpoint
**Exit criteria:** All MVP APIs work against real data; eligibility engine tests confirm correct pass/fail with clear reasons.

---

## Phase 7 — Frontend  *(effort: L)*

**Goal:** Give students a usable interface over the MVP backend.

**Step-by-step:**
1. `npm create vite@latest` with React + TypeScript, then add Tailwind CSS.
2. Build the auth flow (login page, token storage, protected routes).
3. Build Dashboard, Drive listing (with filters), Drive details page.
4. Build Profile page (create/edit student profile).
5. Build Applications page (list, status, withdraw action).
6. Build the AI Assistant chat page against `POST /ai/chat`; add streaming if practical — Groq's low latency makes a streaming UI feel very snappy.
7. Wire everything to the Phase 6 backend; handle loading/error states.
8. Walk through the flow yourself: signup → complete profile → search drives → check eligibility → apply → ask the AI a question.

**Deliverables:** Working student-facing UI covering the MVP flow
**Exit criteria:** A student can complete the entire MVP journey through the UI alone.

---

## Phase 8 — Advanced Features (remaining 9 of 19)  *(effort: L)*

**Goal:** Expand from MVP to the full feature set.

**Step-by-step:**
1. Recommendation engine: implement the weighted score (Skill 40% / Eligibility 20% / Role 20% / CTC 10% / Location 10%), expose `GET /students/me/recommendations`, add a Groq-backed LLM explanation layer on top.
2. Company/CTC comparison: `GET /companies/compare?ids=...` + comparison UI.
3. Analytics: aggregate queries for branch-wise placement %, average/highest CTC, trends, selection ratios; `GET /analytics` + dashboard UI.
4. Interview experiences: chunk and embed into the same Weaviate collection (or a separate one) used by RAG, build a search endpoint, add AI summarization across multiple experiences and AI-generated prep plans.
5. Notifications: on drive creation, run the eligibility engine against all students, score with the recommendation engine, enqueue with an idempotency key, dispatch (in-app first, email optional).
6. Polish deadline awareness, the selection-process explainer, and status tracking if gaps remain from Phase 6.

**Deliverables:** All 19 features from the original spec functional
**Exit criteria:** Every feature in the original feature list works against real or seeded data.

---

## Phase 9 — Testing  *(effort: M)*

**Goal:** Prove this is an engineering project, not just an AI demo.

**Step-by-step:**
1. Unit tests for the eligibility engine and recommendation scoring — cover boundary cases (exact CGPA cutoff, zero backlogs, missing skills).
2. Integration tests for the DB layer, API endpoints, the Weaviate-backed RAG pipeline, and agent tool calls.
3. API tests specifically for auth/authz failure paths (wrong role, wrong student id, missing token).
4. Playwright E2E script for the full student journey (login → filter drives → drive details → eligibility check → apply → verify).
5. k6 load test scripts for drive search, the eligibility endpoint, and `/ai/chat`; capture p50/p95/p99 and error rate — and watch for Groq rate-limit errors under load, since you're on shared developer-tier limits.
6. Wire all of the above into GitHub Actions so they run on every push/PR.

**Deliverables:** Test suites wired into CI, meaningful coverage on eligibility and recommendation logic
**Exit criteria:** CI runs all test tiers on every push; a documented performance baseline exists.

---

## Phase 10 — Production  *(effort: M)*

**Goal:** Make the system deployable, observable, and safe to demo publicly.

**Step-by-step:**
1. Write Dockerfiles for backend, frontend, and each MCP server; add a `docker-compose.yml` for local full-stack spin-up — now including a **Weaviate** service (with both ports mapped) alongside Postgres, Redis, backend, MCP servers, and frontend.
2. Write the GitHub Actions pipeline: lint → unit tests → integration tests → build images → deploy.
3. Add structured logging (`request_id`, `user_id`, `agent_run_id`, `tool_name`, latencies, token usage, errors) via middleware.
4. Harden: move all secrets (`GROQ_API_KEY`, DB creds, JWT secret) to environment variables/a secret manager; if the self-hosted Weaviate container is reachable outside your own network, turn on its API-key auth instead of leaving it anonymous. Add rate limiting on `/ai/chat` and review input-validation coverage.
5. Deploy: pick a host for backend/MCP/frontend and managed Postgres, and run Weaviate as a Docker container on that same host — the same image/ports from Phase 1, no separate cloud service to provision.
6. Optional, once stable: add Prometheus/Grafana/OpenTelemetry.

**Deliverables:** Live deployed system with CI/CD and basic logging/monitoring
**Exit criteria:** The system is publicly demoable, deploys automatically on merge to `main`, and has basic operational visibility.

---

## First Milestone

Start with **Phase 0** only: the architecture doc, ER diagram, repo skeleton, and `.env.example`. Everything from Phase 1 onward depends on those decisions being settled first.
