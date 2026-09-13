# The three MCP servers: placement-mcp, student-mcp, knowledge-mcp.
# Each tool independently re-validates caller identity/role via tool_guard.
#
# Run individually (from backend/):
#   python -m app.mcp.run placement   (default port 8101)
#   python -m app.mcp.run student    (default port 8102)
#   python -m app.mcp.run knowledge  (default port 8103)
#
# Ports/host are configured via MCP_HOST / MCP_*_PORT env vars (see app/core/config.py).

import sys

from mcp.server.fastmcp import FastMCP

from app.core.config import settings
from app.core.observability import setup_logging
from app.db.db import init_db
from app.mcp.knowledge_impls import search_policy_docs_impl
from app.mcp.tool_guard import tool_handler
from app.mcp.tool_impls import (
    check_eligibility_impl,
    create_drive_impl,
    get_application_status_impl,
    get_drive_details_impl,
    get_recommendations_impl,
    get_student_profile_impl,
    search_drives_impl,
    update_application_status_impl,
)
from app.schemas.mcp_tool_schemas import (
    CheckEligibilityInput,
    CreateDriveInput,
    DriveIdInput,
    PolicyQueryInput,
    RecommendationsInput,
    SearchDrivesInput,
    StudentIdInput,
    UpdateApplicationStatusInput,
)


def _server_registry() -> dict[str, dict]:
    """Server registry derived from settings (env-configurable host/ports)."""
    return {
        "placement": {"name": "placement-mcp", "port": settings.MCP_PLACEMENT_PORT},
        "student": {"name": "student-mcp", "port": settings.MCP_STUDENT_PORT},
        "knowledge": {"name": "knowledge-mcp", "port": settings.MCP_KNOWLEDGE_PORT},
    }


SERVERS = _server_registry()


def _health_check(token: str = "", **_kwargs) -> dict:
    """Liveness + dependency probe exposed as a tool on every server (no auth)."""
    from app.core.observability import metrics

    return {"status": "ok", "server_metrics": metrics.snapshot()}


def build_server(kind: str) -> FastMCP:
    cfg = SERVERS[kind]
    server = FastMCP(cfg["name"], host=settings.MCP_HOST, port=cfg["port"])

    # Health/liveness probe available on every server (no auth — pure status data).
    server.add_tool(_health_check, name="health", description="Server health and metrics snapshot.")

    if kind == "placement":
        server.add_tool(
            tool_handler("search_drives", SearchDrivesInput)(search_drives_impl),
            name="search_drives",
            description="Search open placement drives by free text, company, or role.",
        )
        server.add_tool(
            tool_handler("get_drive_details", DriveIdInput)(get_drive_details_impl),
            name="get_drive_details",
            description="Get full details for one drive by its id, including eligibility rules.",
        )
        server.add_tool(
            tool_handler("create_drive", CreateDriveInput, allowed_roles=("admin",))(create_drive_impl),
            name="create_drive",
            description="Create a new placement drive (admin only).",
        )
        server.add_tool(
            tool_handler(
                "update_application_status", UpdateApplicationStatusInput, allowed_roles=("admin",)
            )(update_application_status_impl),
            name="update_application_status",
            description="Move an application to a new status (admin only).",
        )
    elif kind == "student":
        server.add_tool(
            tool_handler("get_student_profile", StudentIdInput)(get_student_profile_impl),
            name="get_student_profile",
            description="Get a student's profile by id. Students may only fetch their own.",
        )
        server.add_tool(
            tool_handler("check_eligibility", CheckEligibilityInput)(check_eligibility_impl),
            name="check_eligibility",
            description="Check whether a student is eligible for a drive (deterministic engine).",
        )
        server.add_tool(
            tool_handler("get_application_status", StudentIdInput)(get_application_status_impl),
            name="get_application_status",
            description="Get all applications and statuses for a student (own data only).",
        )
        server.add_tool(
            tool_handler("get_recommendations", RecommendationsInput)(get_recommendations_impl),
            name="get_recommendations",
            description="Recommended drives ranked by skill match and eligibility.",
        )
    else:  # knowledge
        server.add_tool(
            tool_handler("search_policy_docs", PolicyQueryInput)(search_policy_docs_impl),
            name="search_policy_docs",
            description="Search placement policy documents and job descriptions (RAG).",
        )

    return server


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in SERVERS:
        print("usage: python -m app.mcp.run {placement|student|knowledge}")
        sys.exit(2)
    kind = sys.argv[1]
    setup_logging()
    problems = settings.validate_secrets()
    if problems:
        for p in problems:
            print(f"FATAL: {p}", file=sys.stderr)
        sys.exit(1)
    init_db()
    server = build_server(kind)
    cfg = SERVERS[kind]
    print(f"starting {cfg['name']} on http://{settings.MCP_HOST}:{cfg['port']}/mcp")
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
