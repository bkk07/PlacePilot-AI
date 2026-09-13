# Observability: request-scoped IDs + lightweight structured logging and metrics.
# No external deps — JSON lines on stdout, counters + latency histograms in memory.
# Prometheus/OTel exporters can consume these later (Phase 10 wiring point).

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager

from app.core.config import settings


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = getattr(record, "request_id", None)
        if rid:
            payload["request_id"] = rid
        for key in ("tool", "actor", "duration_ms", "event", "status", "error"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc"] = self.formatException(record.exc_info)[-2000:]
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Idempotent root-logger config: JSON lines, level from settings."""
    root = logging.getLogger()
    if getattr(root, "_placepilot_json", False):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root.handlers = [handler]
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root._placepilot_json = True  # type: ignore[attr-defined]


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


class _Metrics:
    """Thread-safe counters and duration stats; snapshot() for /health and ops."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._durations: dict[str, list[float]] = {}
        self._started = time.time()

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    @contextmanager
    def timed(self, name: str):
        start = time.perf_counter()
        status = "ok"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            with self._lock:
                self._durations.setdefault(f"{name}:{status}", []).append(time.perf_counter() - start)
                self._counters[f"{name}:{status}"] = self._counters.get(f"{name}:{status}", 0) + 1

    def snapshot(self) -> dict:
        with self._lock:
            durations = {}
            for key, values in self._durations.items():
                values = values[-500:]  # bound memory
                self._durations[key] = values
                durations[key] = {
                    "count": len(values),
                    "avg_ms": round(sum(values) / len(values) * 1000, 1),
                    "max_ms": round(max(values) * 1000, 1),
                }
            return {
                "uptime_s": round(time.time() - self._started, 1),
                "counters": dict(self._counters),
                "durations": durations,
            }


metrics = _Metrics()
