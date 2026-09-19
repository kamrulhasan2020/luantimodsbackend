from app.rate_limit import RateLimiter

from .conftest import issue_key


def test_limiter_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(limit=3, window=60)
    assert [limiter.check("k") for _ in range(3)] == [None, None, None]
    retry_after = limiter.check("k")
    assert retry_after is not None and 0 < retry_after <= 60


def test_limiter_keys_are_independent():
    limiter = RateLimiter(limit=1, window=60)
    assert limiter.check("a") is None
    assert limiter.check("b") is None
    assert limiter.check("a") is not None


def test_limiter_window_slides(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: now)
    limiter = RateLimiter(limit=1, window=60)
    assert limiter.check("k") is None
    assert limiter.check("k") is not None
    now += 61
    assert limiter.check("k") is None


def test_limiter_sweeps_idle_keys(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("app.rate_limit.time.monotonic", lambda: now)
    limiter = RateLimiter(limit=5, window=60)
    for i in range(100):
        limiter.check(f"key-{i}")
    now += 200
    limiter.check("fresh")
    assert set(limiter._hits) == {"fresh"}


async def test_over_limit_returns_429_with_retry_after(make_client, alpha):
    client = await make_client(rate_limit_per_minute=3)
    for _ in range(3):
        assert (await client.simulate_get("/books", headers=alpha)).status_code == 200

    resp = await client.simulate_get("/books", headers=alpha)
    assert resp.status_code == 429
    assert 1 <= int(resp.headers["Retry-After"]) <= 60
    assert resp.json == {"detail": "Rate limit exceeded"}


async def test_limit_is_per_key(make_client, engine, alpha):
    beta = await issue_key(engine, "beta")
    client = await make_client(rate_limit_per_minute=1)
    assert (await client.simulate_get("/books", headers=alpha)).status_code == 200
    assert (await client.simulate_get("/books", headers=alpha)).status_code == 429
    assert (await client.simulate_get("/books", headers=beta)).status_code == 200


async def test_failed_auth_is_limited_too(make_client):
    client = await make_client(rate_limit_per_minute=2)
    bad = {"X-API-Key": "lmb_wrong"}
    assert (await client.simulate_get("/books", headers=bad)).status_code == 401
    assert (await client.simulate_get("/books", headers=bad)).status_code == 401
    assert (await client.simulate_get("/books", headers=bad)).status_code == 429


async def test_health_is_not_limited(make_client):
    client = await make_client(rate_limit_per_minute=1)
    for _ in range(5):
        assert (await client.simulate_get("/health")).status_code == 200
