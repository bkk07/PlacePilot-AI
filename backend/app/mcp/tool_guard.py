# The MCP tool guard: independent authorization + input validation + audit for every tool.
# A role is never trusted from the frontend or from the LLM's interpretation of a request.

import inspect
import json
from typing import Callable

from pydantic import BaseModel, ValidationError

from app.core.security import AuthContext, AuthError, verify_token
from app.db.audit import audit_tool_call


class ToolAccessError(Exception):
    """Raised (and converted to a denied result) on failed authorization."""


def _rebind_signature(wrapper: Callable, input_schema: type[BaseModel]) -> None:
    """Expose the schema's fields as explicit parameters so the MCP framework's
    signature introspection produces the right input schema (it can't see **kwargs)."""
    params = [
        inspect.Parameter("token", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
    ]
    for name, field in input_schema.model_fields.items():
        if field.default_factory is not None:
            default = field.default_factory()
        elif field.is_required():
            default = inspect.Parameter.empty
        else:
            default = field.default
        params.append(
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=field.annotation,
                default=default,
            )
        )
    wrapper.__signature__ = inspect.Signature(params)


def tool_handler(
    tool_name: str,
    input_schema: type[BaseModel],
    allowed_roles: tuple[str, ...] = ("student", "admin"),
):
    """Decorate an MCP tool implementation with: token verify -> role check ->
    Pydantic input validation -> execution -> audit. Never trusts caller-supplied
    identity; the token is the only identity source."""

    def decorator(fn: Callable[..., dict]):
        def wrapper(token: str, **kwargs) -> dict:
            try:
                auth = verify_token(token)
            except AuthError as exc:
                audit_tool_call(None, None, tool_name, kwargs, "denied", str(exc))
                return {"error": f"unauthorized: {exc}"}

            if auth.role not in allowed_roles:
                audit_tool_call(auth.user_id, auth.role, tool_name, kwargs, "denied",
                                f"role '{auth.role}' not in {allowed_roles}")
                return {"error": f"forbidden: role '{auth.role}' may not call {tool_name}"}

            try:
                validated = input_schema.model_validate(kwargs)
            except ValidationError as exc:
                audit_tool_call(auth.user_id, auth.role, tool_name, kwargs, "error",
                                f"invalid input: {exc.error_count()} errors")
                return {"error": f"invalid input: {json.loads(exc.json())[0]['msg']}",
                        "details": exc.errors(include_url=False, include_context=False)}

            # Ownership rule: tools carrying a student_id parameter must match the caller.
            student_param = getattr(validated, "student_id", None)
            if student_param is not None and auth.is_student and student_param != auth.user_id:
                audit_tool_call(auth.user_id, auth.role, tool_name, kwargs, "denied",
                                f"cross-student access attempt: {student_param}")
                return {"error": "forbidden: students may only access their own data"}

            try:
                result = fn(auth, validated)
            except ToolAccessError as exc:
                audit_tool_call(auth.user_id, auth.role, tool_name, kwargs, "denied", str(exc))
                return {"error": f"forbidden: {exc}"}
            except Exception as exc:  # tool failure -> partial answer, never a crash
                audit_tool_call(auth.user_id, auth.role, tool_name, kwargs, "error", str(exc))
                return {"error": f"tool {tool_name} failed: {exc}"}

            audit_tool_call(auth.user_id, auth.role, tool_name,
                            kwargs, "ok")
            return result

        _rebind_signature(wrapper, input_schema)
        return wrapper

    return decorator


def require_admin(auth: AuthContext) -> None:
    if not auth.is_admin:
        raise ToolAccessError("admin role required")


def require_owner(auth: AuthContext, student_id: str) -> None:
    """Students can only read their own data; admins may read any student's."""
    if auth.is_student and str(student_id) != auth.user_id:
        raise ToolAccessError("you may only access your own student data")
