from app.repositories.servers import ServerRepository

from .conftest import BOOK, issue_key


async def test_health_needs_no_key(client):
    resp = await client.simulate_get("/health")
    assert resp.status_code == 200
    assert resp.json == {"status": "ok"}


async def test_missing_key_is_401(client):
    resp = await client.simulate_get("/books")
    assert resp.status_code == 401
    assert resp.json == {"detail": "Invalid or missing API key"}
    assert resp.headers["WWW-Authenticate"] == "API-Key"


async def test_wrong_key_is_401(client):
    resp = await client.simulate_get("/books", headers={"X-API-Key": "lmb_nope"})
    assert resp.status_code == 401


async def test_every_books_route_requires_a_key(client):
    for method, path in [
        ("post", "/books"),
        ("get", "/books"),
        ("get", "/books/1"),
        ("patch", "/books/1"),
        ("delete", "/books/1"),
    ]:
        resp = await client.simulate_request(method.upper(), path, json=BOOK)
        assert resp.status_code == 401, (method, path)


async def test_revoked_key_stops_working(client, engine, alpha):
    assert (await client.simulate_get("/books", headers=alpha)).status_code == 200
    await ServerRepository(engine).set_api_key_hash("alpha", None)
    assert (await client.simulate_get("/books", headers=alpha)).status_code == 401


async def test_rotated_key_replaces_old_one(client, engine, alpha):
    new = await issue_key(engine, "gamma")  # a second server, unaffected below
    from app.security import generate_api_key, hash_api_key

    new_key = generate_api_key()
    await ServerRepository(engine).set_api_key_hash("alpha", hash_api_key(new_key))

    assert (await client.simulate_get("/books", headers=alpha)).status_code == 401
    assert (await client.simulate_get("/books", headers={"X-API-Key": new_key})).status_code == 200
    assert (await client.simulate_get("/books", headers=new)).status_code == 200


async def test_unknown_route_is_404(client, alpha):
    resp = await client.simulate_get("/nope", headers=alpha)
    assert resp.status_code == 404
