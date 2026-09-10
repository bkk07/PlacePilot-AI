# Audit logging: every MCP tool call logs who called it, with what params, and result status.

import logging

from sqlalchemy import JSON as SAJSON
from sqlalchemy import String

from app.db.db import get_session_factory
from app.db.models import AuditLog

logger = logging.getLogger("audit")


def audit_tool_call(
    actor_id: str | None,
    actor_role: str | None,
    tool_name: str,
    args: dict,
    result_status: str,
    detail: str | None = None,
) -> None:
    """Persist an audit row; failures must never break the tool call itself."""
    try:
        session = get_session_factory()()
        try:
            session.add(
                AuditLog(
                    actor_id=actor_id,
                    actor_role=actor_role,
                    tool_name=tool_name,
                    args=args,
                    result_status=result_status,
                    detail=detail,
                )
            )
            session.commit()
        finally:
            session.close()
    except Exception as exc:
        logger.warning("audit log write failed for %s: %s", tool_name, exc)
