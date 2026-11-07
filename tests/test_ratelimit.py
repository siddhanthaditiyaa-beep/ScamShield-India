from fastapi.testclient import TestClient

import app.main as main
from app.ratelimit import RateLimiter


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_per_visitor_limit_and_window_reset():
    clock = Clock()
    rl = RateLimiter(per_ip=3, total=100, window=60, clock=clock)
    assert [rl.allow("a") for _ in range(4)] == [True, True, True, False]
    assert rl.allow("b")  # another visitor is not affected
    clock.t += 61
    assert rl.allow("a")  # the window has passed


def test_overall_cap_holds_even_for_new_visitors():
    rl = RateLimiter(per_ip=10, total=3, window=60, clock=Clock())
    assert [rl.allow(f"ip{i}") for i in range(4)] == [True, True, True, False]


def test_memory_stays_bounded():
    clock = Clock()
    rl = RateLimiter(per_ip=5, total=10**6, window=60, max_ips=50, clock=clock)
    for i in range(500):
        rl.allow(f"ip{i}")
    assert len(rl._by_ip) <= 50


def test_api_returns_429_after_limit(monkeypatch):
    monkeypatch.setattr(main, "limiter", RateLimiter(per_ip=2, total=100))
    client = TestClient(main.app)
    body = {"message": "hello there"}
    assert client.post("/api/analyze", json=body).status_code == 200
    assert client.post("/api/analyze", json=body).status_code == 200
    assert client.post("/api/analyze", json=body).status_code == 429
    # health check is never limited
    assert client.get("/api/health").status_code == 200
