"""A tiny in-memory rate limiter for the public demo.

Two limits, both over a sliding window (default 60 seconds):
  - per visitor: at most `per_ip` checks
  - everyone together: at most `total` checks, so one flood cannot use up the free server

Honest limits: it lives in memory (a restart clears it) and the visitor address comes from the
X-Forwarded-For header, which a determined person can fake. The overall cap still holds then.
This protects a free demo from accidents and casual abuse. It is not security-grade.
"""
from __future__ import annotations

import time
from collections import deque


class RateLimiter:
    def __init__(self, per_ip: int = 20, total: int = 300, window: float = 60.0,
                 max_ips: int = 5000, clock=time.monotonic):
        self.per_ip, self.total, self.window, self.max_ips, self.clock = per_ip, total, window, max_ips, clock
        self._by_ip: dict[str, deque] = {}
        self._all: deque = deque()

    @staticmethod
    def _drop_old(q: deque, cutoff: float) -> None:
        while q and q[0] <= cutoff:
            q.popleft()

    def allow(self, ip: str) -> bool:
        now = self.clock()
        cutoff = now - self.window
        self._drop_old(self._all, cutoff)
        if len(self._all) >= self.total:
            return False
        q = self._by_ip.setdefault(ip, deque())
        self._drop_old(q, cutoff)
        if len(q) >= self.per_ip:
            return False
        q.append(now)
        self._all.append(now)
        if len(self._by_ip) > self.max_ips:  # keep memory bounded
            for key in [k for k, v in self._by_ip.items() if not v or v[-1] <= cutoff]:
                del self._by_ip[key]
            while len(self._by_ip) > self.max_ips:
                del self._by_ip[next(iter(self._by_ip))]
        return True
