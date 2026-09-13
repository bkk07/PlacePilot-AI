# Unit tests for the MCP tool guard: signature rebinding, ownership rule,
# error codes, and audit paths — no servers or live DB required.

import json

import pytest
from pydantic import BaseModel, Field

from app.mcp import tool_guard


class _DummyInput(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    top_k: int = Field(default=3, ge=1, le=10)


def _make_tool(input_schema, impl, allowed_roles=("student", "admin")):
    return tool_guard.tool_handler("dummy", input_schema, allowed_roles=allowed_roles)(impl)


class _FakeAuth:
    def __init__(self, user_id, role):
        self.user_id = user_id
        self.role = role

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_admin(self):
        return self.role == "admin"


def test_rebind_signature_exposes_schema_fields():
    import inspect

    def wrapper(token, **kwargs):
        return {}

    tool_guard._rebind_signature(wrapper, _DummyInput)
    sig = inspect.signature(wrapper)
    params = list(sig.parameters)
    assert params[0] == "token"
    assert "student_id" in params and "top_k" in params
    assert sig.parameters["top_k"].default == 3
    assert sig.parameters["student_id"].default is inspect.Parameter.empty


def test_coerce_and_validate_via_guard(monkeypatch):
    monkeypatch.setattr(tool_guard, "verify_active_user", lambda t: _FakeAuth("u1", "student"))
    monkeypatch.setattr(tool_guard, "audit_tool_call", lambda *a, **k: None)

    def impl(auth, inp):
        return {"ok": True, "k": inp.top_k}

    tool = _make_tool(_DummyInput, impl)
    result = tool(token="x", student_id="u1", top_k="5")  # string like the LLM would emit
    # NOTE: the guard validates via pydantic, which coerces "5" -> 5
    assert result == {"ok": True, "k": 5}


def test_cross_student_denied_with_code(monkeypatch):
    monkeypatch.setattr(tool_guard, "verify_active_user", lambda t: _FakeAuth("u1", "student"))
    monkeypatch.setattr(tool_guard, "audit_tool_call", lambda *a, **k: None)

    def impl(auth, inp):
        return {"ok": True}

    tool = _make_tool(_DummyInput, impl)
    result = tool(token="x", student_id="someone-else")
    assert result["code"] == "forbidden"
    assert "forbidden" in result["error"]


def test_invalid_input_returns_details_and_code(monkeypatch):
    monkeypatch.setattr(tool_guard, "verify_active_user", lambda t: _FakeAuth("u1", "student"))
    monkeypatch.setattr(tool_guard, "audit_tool_call", lambda *a, **k: None)

    def impl(auth, inp):
        return {"ok": True}

    tool = _make_tool(_DummyInput, impl)
    result = tool(token="x", student_id="u1", top_k=99)  # violates le=10
    assert result["code"] == "invalid_input"
    assert "details" in result


def test_role_denied_for_admin_tool(monkeypatch):
    monkeypatch.setattr(tool_guard, "verify_active_user", lambda t: _FakeAuth("u1", "student"))
    monkeypatch.setattr(tool_guard, "audit_tool_call", lambda *a, **k: None)

    def impl(auth, inp):
        return {"ok": True}

    tool = _make_tool(_DummyInput, impl, allowed_roles=("admin",))
    result = tool(token="x", student_id="u1")
    assert result["code"] == "forbidden"


def test_deactivated_user_rejected(monkeypatch):
    """verify_active_user must be consulted — a stale token of a deleted user fails."""

    def _raise(token):
        from app.core.security import AuthError

        raise AuthError("user not found or inactive")

    monkeypatch.setattr(tool_guard, "verify_active_user", _raise)
    monkeypatch.setattr(tool_guard, "audit_tool_call", lambda *a, **k: None)

    def impl(auth, inp):
        return {"ok": True}

    tool = _make_tool(_DummyInput, impl)
    result = tool(token="x", student_id="u1")
    assert result["code"] == "unauthorized"


def test_tool_exception_becomes_error_dict(monkeypatch):
    monkeypatch.setattr(tool_guard, "verify_active_user", lambda t: _FakeAuth("u1", "student"))
    monkeypatch.setattr(tool_guard, "audit_tool_call", lambda *a, **k: None)

    def impl(auth, inp):
        raise RuntimeError("db down")

    tool = _make_tool(_DummyInput, impl)
    result = tool(token="x", student_id="u1")
    assert result["code"] == "tool_error"
    assert "db down" in result["error"]
