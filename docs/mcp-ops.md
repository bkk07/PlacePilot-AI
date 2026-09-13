# MCP Operations Guide

Three MCP servers expose the placement tools over streamable-http. Every tool
independently re-verifies the caller's JWT (identity + role + user liveness)
before executing, and writes an audit row for every outcome.

## Servers

| Server | Tools | Default port |
|---|---|---|
| placement-mcp | `search_drives`, `get_drive_details`, `create_drive` (admin), `update_application_status` (admin) | 8101 |
| student-mcp | `get_student_profile`, `check_eligibility`, `get_application_status`, `get_recommendations` | 8102 |
| knowledge-mcp | `search_policy_docs` (RAG over Weaviate) | 8103 |

Every server also exposes an unauthenticated `health` tool returning
`{status, server_metrics}` — liveness plus in-process counters/latency stats.

## Configuration (env)

| Variable | Default | Purpose |
|---|---|---|
| `MCP_HOST` | `127.0.0.1` | Bind host for all servers (bind `0.0.0.0` only inside a trusted network/container) |
| `MCP_PLACEMENT_PORT` / `MCP_STUDENT_PORT` / `MCP_KNOWLEDGE_PORT` | 8101/8102/8103 | Server ports |
| `MCP_PLACEMENT_URL` / `MCP_STUDENT_URL` / `MCP_KNOWLEDGE_URL` | derived from host+ports | Agent-side URLs (set when servers run on another host, e.g. Docker) |
| `MCP_TOOL_TIMEOUT_S` | 20 | Per-call timeout in the agent's MCP client |
| `MCP_TOOL_RETRIES` | 1 | Transport-error retries with backoff |
| `MCP_CATALOG_TTL_S` | 300 | Tool-catalog cache TTL (auto re-sync) |
| `JWT_SECRET` | — | **Required**; servers refuse to start on the default value |

Ports are configured in one place (`app/core/config.py`); the server registry
and the client URL map both derive from it — no more duplicated constants.

## Running

```bash
# from backend/
python -m app.mcp.run placement
python -m app.mcp.run student
python -m app.mcp.run knowledge
```

Or everything at once:

```bash
docker compose up -d
```

The compose stack runs Postgres, Redis, Weaviate, the API, and all three MCP
servers with health checks and volume persistence. `JWT_SECRET` must be set in
`.env` (compose refuses to boot otherwise).

## Client behavior (the agent side)

- One shared `MultiServerMCPClient` per process; catalog cached with a TTL and
  refreshed under a lock. Unknown tool names trigger a one-shot forced refresh.
- Tool-name collisions across servers are logged and counted (`mcp_tool_name_collisions`).
- String args from the LLM are coerced to the schema's `integer`/`number`/`boolean` types before the call.
- Timeouts and transport failures return `{"error": ..., "code": "transport_error"}` — never crash the agent run.

## Error codes

Every tool error is a dict with a stable `code`:

| code | meaning |
|---|---|
| `unauthorized` | JWT invalid/expired, or user deleted/deactivated |
| `forbidden` | role not allowed, or cross-student access |
| `invalid_input` | Pydantic validation failed (`details` included) |
| `invalid_transition` | application status change rejected by the state machine (`allowed_next` included) |
| `tool_error` | unexpected failure inside the tool |

## Monitoring

- JSON-structured logs on stdout (`mcp.tools` logger) with tool name, actor, duration.
- In-memory counters/latency histograms via `app.core.observability.metrics`; exposed through each server's `health` tool and the API `/health` endpoint (`metrics` field).
- Audit trail: every call writes a row to `audit_log` (actor, role, tool, args, status, detail).

## Runbook

- **A server dies:** the agent's client returns `transport_error` for that server's tools; other servers keep working. Restart the process; the catalog TTL re-syncs automatically within `MCP_CATALOG_TTL_S` (or immediately on unknown-tool).
- **Catalog is stale:** `app.agent.mcp_client.reset_client()` drops caches (tests do this too); otherwise wait for the TTL.
- **Full RAG re-ingest:** `python -m app.ai.ingest --rebuild`; incremental: `python -m app.ai.ingest --prune`.
- **Weak JWT secret:** MCP servers exit at startup; the API logs a warning. Set `JWT_SECRET` in `.env`.
