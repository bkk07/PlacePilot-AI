# placement-mcp

Served from `backend/app/mcp/servers.py` — run with `python -m app.mcp.run placement` (port 8101).

Tools: `search_drives`, `get_drive_details`, `create_drive` (admin), `update_application_status` (admin).

Backed by PostgreSQL. Every call re-verifies the caller's JWT and role, validates inputs with
Pydantic, and writes an audit row.