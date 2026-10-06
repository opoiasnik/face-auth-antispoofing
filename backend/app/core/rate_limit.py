"""Fixed-window rate limiting with in-memory and Redis backends."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from redis import Redis


class RateLimiter(Protocol):
    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Register a hit; return ``False`` when the limit for the window is exceeded."""
        ...


class InMemoryRateLimiter:
    """Single-process limiter. Use :class:`RedisRateLimiter` with multiple workers."""

    def __init__(self) -> None:
        self._buckets: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        window = int(time.time() // window_seconds)
        with self._lock:
            current_window, count = self._buckets.get(key, (window, 0))
            if current_window != window:
                count = 0
            count += 1
            self._buckets[key] = (window, count)
            if len(self._buckets) > 50_000:
                self._evict(window)
        return count <= limit

    def _evict(self, window: int) -> None:
        stale = [k for k, (w, _) in self._buckets.items() if w != window]
        for k in stale:
            del self._buckets[k]


class RedisRateLimiter:
    def __init__(self, client: Redis, prefix: str = "fa:rl:") -> None:
        self._client = client
        self._prefix = prefix

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        window = int(time.time() // window_seconds)
        redis_key = f"{self._prefix}{key}:{window}"
        pipe = self._client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds)
        count, _ = pipe.execute()
        return int(count) <= limit
