"""Per-source token bucket rate limiter (thread-safe)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class TokenBucket:
    def __init__(self, rate_per_sec: float, burst: float | None = None) -> None:
        self.rate = rate_per_sec
        self.capacity = burst if burst is not None else max(1.0, rate_per_sec)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                # sleep just enough for the remainder
                needed = (tokens - self._tokens) / self.rate
                time.sleep(needed)


_limiters: dict[str, TokenBucket] = {}
_init_lock = threading.Lock()


DEFAULTS: dict[str, float] = {
    "yfinance": 1.0,   # 1 req/sec per ticker
    "fred": 2.0,       # 120/min
    "finnhub": 1.0,    # 60/min
    "edgar": 10.0,     # 10/sec, per their guidelines
    "google_rss": 0.5, # polite
    "reddit": 1.0,     # 60/min
    "noaa": 2.0,
}


def for_source(name: str) -> TokenBucket:
    with _init_lock:
        if name not in _limiters:
            _limiters[name] = TokenBucket(DEFAULTS.get(name, 1.0))
        return _limiters[name]
