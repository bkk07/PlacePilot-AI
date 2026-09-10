# Unit tests for the LLM service: happy path, malformed-output retry path, hard-fail path.
# The Groq client is faked — no network needed for these tests.

import json
from unittest.mock import patch

import pytest

from app.ai.llm_service import (
    LLMOutputError,
    MODEL_REASONING,
    call_llm,
    generate_structured,
    parse_structured,
)
from app.schemas.llm_schemas import EligibilityExplanation


class FakeContent:
    def __init__(self, text: str):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]


class FakeResponse:
    """Side effect for call_llm: returns queued raw strings, one per call."""

    def __init__(self, texts: list[str]):
        self._texts = texts
        self.calls = 0

    def __call__(self, *args, **kwargs):
        text = self._texts[min(self.calls, len(self._texts) - 1)]
        self.calls += 1
        return text


VALID = {
    "eligible": False,
    "summary": "Not eligible for Nimbus drive",
    "reasons": ["CGPA 6.2 is below the required 7.0"],
    "missing_requirements": ["CGPA >= 7.0"],
}


def test_parse_structured_happy_path():
    result = parse_structured(json.dumps(VALID), EligibilityExplanation)
    assert result.eligible is False
    assert result.missing_requirements == ["CGPA >= 7.0"]


def test_parse_structured_strips_markdown_fences():
    fenced = f"```json\n{json.dumps(VALID)}\n```"
    result = parse_structured(fenced, EligibilityExplanation)
    assert result.eligible is False


def test_generate_structured_retries_once_then_succeeds():
    fake = FakeResponse(["not json at all", json.dumps(VALID)])
    with patch("app.ai.llm_service.call_llm", side_effect=fake):
        result = generate_structured([], schema=EligibilityExplanation, config=MODEL_REASONING)
    assert result.eligible is False
    assert fake.calls == 2  # initial call + one corrective retry


def test_generate_structured_fails_loudly_after_retry():
    fake = FakeResponse(["garbage", "still garbage"])
    with patch("app.ai.llm_service.call_llm", side_effect=fake):
        with pytest.raises(LLMOutputError):
            generate_structured([], schema=EligibilityExplanation, config=MODEL_REASONING)
    assert fake.calls == 2


def test_generate_structured_rejects_schema_valid_json_but_wrong_types():
    wrong = {"eligible": "yes", "summary": "x", "reasons": "not-a-list"}
    fake = FakeResponse([json.dumps(wrong), json.dumps(VALID)])
    with patch("app.ai.llm_service.call_llm", side_effect=fake):
        result = generate_structured([], schema=EligibilityExplanation, config=MODEL_REASONING)
    assert result.eligible is False


def test_generate_structured_rejects_schema_valid_json_but_wrong_types():
    wrong = {"eligible": "yes", "summary": "x", "reasons": "not-a-list"}
    fake = FakeResponse([json.dumps(wrong), json.dumps(VALID)])
    with patch("app.ai.llm_service.call_llm", side_effect=fake):
        result = generate_structured([], schema=EligibilityExplanation, config=MODEL_REASONING)
    assert result.eligible is False


def test_call_llm_json_mode_passthrough(monkeypatch):
    """call_llm must request json_object response format when a schema is supplied."""
    captured: dict = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeContent(json.dumps(VALID))

    class FakeChat:
        completions = FakeCompletions()

    class FakeGroqClient:
        chat = FakeChat()

    monkeypatch.setattr(
        "app.ai.llm_service.get_groq_client", lambda: FakeGroqClient()
    )
    raw = call_llm([], config=MODEL_REASONING, json_schema={"type": "object"})
    assert json.loads(raw) == VALID
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["model"] == MODEL_REASONING.name


def test_call_llm_4xx_fails_fast_without_retry(monkeypatch):
    """Deterministic client errors (400/404) must not be retried."""
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(1)
            exc = Exception("Error code: 400 - bad request")
            exc.status_code = 400
            raise exc

    class FakeChat:
        completions = FakeCompletions()

    class FakeGroqClient:
        chat = FakeChat()

    monkeypatch.setattr(
        "app.ai.llm_service.get_groq_client", lambda: FakeGroqClient()
    )
    with pytest.raises(LLMOutputError, match="400"):
        call_llm([], config=MODEL_REASONING)
    assert len(calls) == 1


def test_call_llm_5xx_retried_once(monkeypatch):
    """Transient server errors get exactly one retry."""
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                exc = Exception("Error code: 503 - overloaded")
                exc.status_code = 503
                raise exc
            return FakeContent(json.dumps(VALID))

    class FakeChat:
        completions = FakeCompletions()

    class FakeGroqClient:
        chat = FakeChat()

    monkeypatch.setattr(
        "app.ai.llm_service.get_groq_client", lambda: FakeGroqClient()
    )
    raw = call_llm([], config=MODEL_REASONING)
    assert len(calls) == 2
    assert json.loads(raw) == VALID
