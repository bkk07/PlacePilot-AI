# Groq LLM service: model config, timeouts, retries, and structured-output parsing.
#
# Parse failure policy: retry once with a corrective prompt, then raise LLMOutputError —
# raw text is NEVER returned downstream as if it were structured data.

import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TypeVar

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


@dataclass
class UsageRecord:
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0


@dataclass
class UsageTracker:
    """Accumulates token usage per model for one measured operation (e.g. an eval run)."""

    records: dict[str, UsageRecord] = field(default_factory=dict)

    def add(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        rec = self.records.setdefault(model, UsageRecord(model=model))
        rec.prompt_tokens += prompt_tokens
        rec.completion_tokens += completion_tokens
        rec.calls += 1

    @property
    def total_prompt_tokens(self) -> int:
        return sum(r.prompt_tokens for r in self.records.values())

    @property
    def total_completion_tokens(self) -> int:
        return sum(r.completion_tokens for r in self.records.values())

    @property
    def total_calls(self) -> int:
        return sum(r.calls for r in self.records.values())

    def summary(self) -> dict:
        return {
            "models": {m: vars(r) for m, r in self.records.items()},
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "calls": self.total_calls,
        }


_usage_state = threading.local()


@contextmanager
def track_usage():
    """Collect token usage from all LLM calls made inside the block."""
    tracker = UsageTracker()
    _usage_state.tracker = tracker
    try:
        yield tracker
    finally:
        _usage_state.tracker = None


def _record_usage(model: str, response) -> None:
    tracker = getattr(_usage_state, "tracker", None)
    if tracker is None:
        return
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    tracker.add(
        model,
        getattr(usage, "prompt_tokens", 0) or 0,
        getattr(usage, "completion_tokens", 0) or 0,
    )


class LLMOutputError(Exception):
    """Raised when the LLM fails to produce schema-valid output after one retry."""


def _is_transient(exc: Exception) -> bool:
    """429 (rate limit) and 5xx/network errors are worth retrying; other 4xx are
    deterministic (bad request, invalid model) — retrying cannot fix them."""
    status = getattr(exc, "status_code", None)
    if status is not None:
        if status == 429:
            return True
        return not (400 <= status < 500)
    return True  # network/timeout errors with no status — assume transient


@dataclass(frozen=True)
class ModelConfig:
    name: str
    timeout: float  # seconds
    max_tokens: int
    temperature: float


# Reasoning-heavy use cases: eligibility explanations, policy Q&A, recommendation reasoning.
MODEL_REASONING = ModelConfig(
    name=settings.GROQ_REASONING_MODEL,
    timeout=30.0,
    max_tokens=1024,
    temperature=0.1,
)
# Lightweight/low-latency use cases.
MODEL_LIGHT = ModelConfig(
    name=settings.GROQ_LIGHT_MODEL,
    timeout=15.0,
    max_tokens=512,
    temperature=0.2,
)

CORRECTIVE_PROMPT = (
    "Your previous reply was not valid JSON matching the required schema. "
    "Reply again with ONLY a JSON object — no prose, no markdown fences — "
    "conforming exactly to the schema described in the original question."
)


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise LLMOutputError("GROQ_API_KEY is not configured")
    return Groq(api_key=settings.GROQ_API_KEY, timeout=settings.GROQ_TIMEOUT)


def call_llm(
    messages: list[dict],
    config: ModelConfig = MODEL_REASONING,
    json_schema: dict | None = None,
    max_retries: int = 2,
) -> str:
    """One Groq chat call with timeout + transient-error retry (exponential backoff).
    429 rate limits and 5xx/network errors are retried; other 4xx fail fast."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "model": config.name,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "timeout": config.timeout,
            }
            if json_schema is not None:
                kwargs["response_format"] = {"type": "json_object"}
            response = get_groq_client().chat.completions.create(**kwargs)
            _record_usage(config.name, response)
            return response.choices[0].message.content or ""
        except Exception as exc:
            last_exc = exc
            if not _is_transient(exc) or attempt == max_retries:
                break
            time.sleep(min(1.5 * (2**attempt), 10.0))
    raise LLMOutputError(f"LLM call failed after retry: {last_exc}")


def parse_structured(raw: str, schema: type[T]) -> T:
    """Parse raw LLM text against a Pydantic schema. Strips markdown fences first."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(text)  # raises on malformed JSON
    return schema.model_validate(data)  # raises on schema violation


def generate_structured(
    messages: list[dict],
    schema: type[T],
    config: ModelConfig = MODEL_REASONING,
) -> T:
    """Call the LLM, validate output against the schema; on failure retry once with a
    corrective prompt, then raise LLMOutputError. Never returns raw text."""
    try:
        raw = call_llm(messages, config=config, json_schema=schema.model_json_schema())
    except LLMOutputError:
        # Some model/prompt combos fail Groq's server-side JSON validation (400
        # json_validate_failed). Fall back to free text — our parser enforces the schema.
        raw = call_llm(messages, config=config)
    try:
        return parse_structured(raw, schema)
    except (json.JSONDecodeError, ValidationError):
        pass  # fall through to the corrective retry

    retry_raw = call_llm(
        messages + [{"role": "user", "content": CORRECTIVE_PROMPT}],
        config=config,
    )
    try:
        return parse_structured(retry_raw, schema)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMOutputError(
            f"LLM output failed schema validation after one corrective retry: {exc}"
        ) from exc
