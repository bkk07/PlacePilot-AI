# Security Model

## Roles

| Role | Permissions |
|---|---|
| **Student** | View drives/companies, check eligibility, apply, track/withdraw own applications, view recommendations, ask AI assistant, view own profile/history only |
| **Admin** (placement admin) | Create/update drives, upload documents, manage companies, update application statuses, manage policies, view analytics |
| **Alumni** (future, not MVP) | Submit interview experiences, limited read access. Enum value reserved now; no flows built. |

## Auth mechanism

- **JWT bearer tokens.** Login (`POST /auth/login`) verifies password hash, returns a signed JWT containing `sub` (user id), `role`, and `exp`.
- Passwords hashed with bcrypt (never stored in plaintext).
- Tokens carry no mutable state; role is re-read from the DB on privileged operations if staleness is a concern.

## The core rule

> **A role is never trusted from the frontend or from the LLM's interpretation of a request.** Every API endpoint and every MCP tool independently re-checks the caller's identity and role before doing anything.

## Enforcement layers

### 1. API layer (Phase 6)
- Every endpoint requires a valid JWT (dependency injection: `get_current_user`).
- Role checks as route dependencies: admin-only routes declare `require_role('admin')`.
- Students can only access their own data — `student_id` is taken from the JWT `sub`, never from the request body for identity purposes.

### 2. MCP tool layer (Phase 4)
- Every MCP tool handler receives an auth context (extracted from the caller's token, propagated by the agent).
- Before executing, each tool re-validates: identity exists, role matches the tool's allowed roles.
- **Negative rule:** a student's token can never fetch another student's profile, applications, or status — `get_student_profile(student_b_id)` with student A's token must fail.
- Admin-only tools (`create_drive`, `update_application_status`, …) reject student tokens at the MCP layer too, not just the API layer.

### 3. AI/LLM guardrails
- Eligibility is decided by the deterministic rule engine only; the LLM explains the result, never determines it.
- RAG answers must cite retrieved chunks; if retrieval finds nothing relevant, the system declines rather than answering from general knowledge.
- All LLM outputs are validated against Pydantic schemas; malformed output is retried once with a corrective prompt, then fails loudly.
- User input is never treated as a system instruction — MCP tools validate and sanitize all inputs before execution.
- AI responses are checked to never leak another student's PII (verified in the Phase 5 eval set).
- Rate limits and token caps on LLM/embedding calls (Groq TPM/RPM aware).

### 4. Data & input guardrails
- Pydantic validation on every API and MCP tool input.
- SQLAlchemy ORM / parameterized queries only — no raw string-built SQL.
- Upload validation: file type + size limits on document ingestion.
- Audit logging on sensitive tool and API calls: who, what params, result status.

### 5. Business-logic guardrails
- Application status changes follow the strict state machine (Not Applied → Applied → Shortlisted → Interview → Offer → Selected/Rejected, plus Withdrawn) — no arbitrary transitions; every change is recorded in `application_status_history`.
- Idempotency keys on application submission and notification dispatch.
- The eligibility engine is the single source of truth; the eval suite (Phase 5) checks the LLM's explanation never contradicts the engine's decision.

## Threat checklist

| Threat | Mitigation |
|---|---|
| Student reads another student's data | JWT `sub` + ownership check at API and MCP layers; negative test in Phase 4 |
| Student performs admin action | `require_role('admin')` at API; role re-check in every admin MCP tool |
| LLM hallucinating eligibility or CTC facts | Deterministic engine for decisions; RAG citations for facts; decline when ungrounded |
| Prompt injection via user input | Inputs validated/sanitized before tool execution; user text never becomes system instructions |
| Malformed LLM output downstream | Pydantic schema validation, retry-once-then-fail policy |
| Duplicate submissions on retry | Idempotency keys |
| Secret leakage | All secrets in env vars; never logged; `.env` gitignored |
