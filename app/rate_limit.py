import time
from collections import deque


class RateLimiter:
    """In-memory sliding-window limiter.

    Only accurate within a single process, so the app must run with one worker.
    Swap for a shared store (e.g. Redis) before scaling past that.
    """

    def __init__(self, limit: int, window: float = 60.0) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = {}
        self._next_sweep = time.monotonic() + window

    def check(self, key: str) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until a slot frees up."""
        now = time.monotonic()
        self._sweep(now)

        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(hits[0] + self.window - now, 0.0)
        hits.append(now)
        return None

    def _sweep(self, now: float) -> None:
        """Drop idle keys so the dict can't grow without bound."""
        if now < self._next_sweep:
            return
        self._next_sweep = now + self.window
        cutoff = now - self.window
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]:
            del self._hits[key]
