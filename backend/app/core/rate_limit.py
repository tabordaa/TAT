"""Brute-force protection for the login: counts failures per time window.

State lives in this process's memory, which fits a single API instance. With
several instances each one would count on its own and the limit would multiply:
at that point the counters belong in Redis or the database.
"""

import math
import threading
import time
from collections.abc import Callable


class FailureCounter:
    """Blocks a key once it fails `max_failures` times within `window_seconds`."""

    # Bound on tracked keys: an attacker rotating emails must not exhaust memory.
    MAX_KEYS = 10_000

    def __init__(
        self,
        max_failures: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_failures = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, list[float]] = {}
        # FastAPI runs sync endpoints in a thread pool: requests really overlap.
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        return [t for t in self._failures.get(key, []) if now - t < self._window]

    def retry_after(self, key: str) -> int:
        """Seconds until `key` may try again; 0 if it is not blocked."""
        with self._lock:
            now = self._clock()
            recent = self._recent(key, now)
            if len(recent) < self._max_failures:
                return 0
            # Blocked until enough old failures leave the window.
            unblocks_at = recent[-self._max_failures] + self._window
            return max(1, math.ceil(unblocks_at - now))

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            if key not in self._failures and len(self._failures) >= self.MAX_KEYS:
                self._prune(now)
            self._failures[key] = [*self._recent(key, now), now]

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()

    def _prune(self, now: float) -> None:
        self._failures = {
            key: recent
            for key in self._failures
            if (recent := self._recent(key, now))
        }
        # Everything is still recent: drop the oldest half rather than grow.
        if len(self._failures) >= self.MAX_KEYS:
            by_age = sorted(self._failures, key=lambda k: self._failures[k][-1])
            for key in by_age[: self.MAX_KEYS // 2]:
                del self._failures[key]


class LoginThrottle:
    """Two limits: one account from one IP, and one IP against any account.

    The account limit is tied to the IP on purpose. Counting per email alone
    would let anyone lock a colleague out just by failing on their email.
    """

    def __init__(
        self,
        account_failures: int,
        ip_failures: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._accounts = FailureCounter(account_failures, window_seconds, clock)
        self._ips = FailureCounter(ip_failures, window_seconds, clock)

    def retry_after(self, ip: str, email: str) -> int:
        return max(
            self._accounts.retry_after(f"{ip}|{email}"),
            self._ips.retry_after(ip),
        )

    def record_failure(self, ip: str, email: str) -> None:
        self._accounts.record_failure(f"{ip}|{email}")
        self._ips.record_failure(ip)

    def record_success(self, ip: str, email: str) -> None:
        # The IP counter stays: one valid login must not erase a spray attack.
        self._accounts.reset(f"{ip}|{email}")

    def clear(self) -> None:
        self._accounts.clear()
        self._ips.clear()
