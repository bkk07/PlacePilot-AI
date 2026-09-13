# Per-user in-memory sliding-window rate limiter (shared shape with the auth
# login limiter). Redis-backed distribution can swap in later without changing
# call sites.

import threading
import time


class RateLimiter:
    def __init__(self, max_attempts: int, window_sec: int):
        self.max_attempts = max_attempts
        self.window_sec = window_sec
        self._lock = threading.Lock()
        self._attempts: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        """Record one attempt for `key`; return False when over the limit."""
        now = time.time()
        with self._lock:
            # Bound memory: occasional sweep of stale keys
            if len(self._attempts) > 10_000:
                self._attempts = {
                    k: v for k, v in self._attempts.items() if now - (v[-1] if v else 0) < self.window_sec
                }
            times = [t for t in self._attempts.get(key, []) if now - t < self.window_sec]
            if len(times) >= self.max_attempts:
                self._attempts[key] = times
                return False
            times.append(now)
            self._attempts[key] = times
            return True
