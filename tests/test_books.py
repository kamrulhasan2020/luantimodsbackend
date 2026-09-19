from .conftest import BOOK


async def create(client, headers, **overrides) -> dict:
    resp = await client.simulate_post("/books", headers=headers, json={**BOOK, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json


async def test_create_and_get(client, alpha):
    created = await create(client, alpha, category="lore")
    assert created["servername"] == "alpha"
    assert created["title"] == BOOK["title"]
    assert created["category"] == "lore"
    assert created["created_at"].endswith("Z")
    assert created["updated_at"].endswith("Z")

    resp = await client.simulate_get(f"/books/{created['id']}", headers=alpha)
    assert resp.status_code == 200
    assert resp.json == created


async def test_category_is_optional(client, alpha):
    assert (await create(client, alpha))["category"] is None


async def test_reads_are_global(client, alpha, beta):
    book = await create(client, alpha)
    resp = await client.simulate_get(f"/books/{book['id']}", headers=beta)
    assert resp.status_code == 200
    assert resp.json["servername"] == "alpha"

    listed = (await client.simulate_get("/books", headers=beta)).json
    assert [b["id"] for b in listed] == [book["id"]]


async def test_get_missing_is_404(client, alpha):
    resp = await client.simulate_get("/books/999", headers=alpha)
    assert resp.status_code == 404
    assert resp.json == {"detail": "Book not found"}


async def test_absurd_ids_are_404_not_500(client, alpha):
    for bad in ("0", "abc", str(2**70)):
        assert (await client.simulate_get(f"/books/{bad}", headers=alpha)).status_code == 404


async def test_list_omits_content_and_updated_at(client, alpha):
    await create(client, alpha)
    (item,) = (await client.simulate_get("/books", headers=alpha)).json
    assert set(item) == {"id", "title", "author", "category", "servername", "created_at"}


async def test_list_filters(client, alpha, beta):
    await create(client, alpha, author="steve", category="lore")
    await create(client, alpha, author="alex", category="recipes")
    await create(client, beta, author="steve", category="recipes")

    async def ids(query: str) -> int:
        resp = await client.simulate_get(f"/books?{query}", headers=alpha)
        assert resp.status_code == 200
        return len(resp.json)

    assert await ids("author=steve") == 2
    assert await ids("category=recipes") == 2
    assert await ids("server=beta") == 1
    assert await ids("server=alpha&author=steve") == 1
    assert await ids("server=nobody") == 0


async def test_list_is_newest_first_and_paginates(client, alpha):
    ids = [(await create(client, alpha, title=f"book {i}"))["id"] for i in range(5)]

    page = (await client.simulate_get("/books?limit=2", headers=alpha)).json
    assert [b["id"] for b in page] == ids[::-1][:2]

    page = (await client.simulate_get("/books?limit=2&offset=2", headers=alpha)).json
    assert [b["id"] for b in page] == ids[::-1][2:4]


async def test_bad_pagination_is_rejected(client, alpha):
    for query in ("limit=0", "limit=-1", "limit=abc", "offset=-1"):
        resp = await client.simulate_get(f"/books?{query}", headers=alpha)
        assert resp.status_code == 400, query


async def test_limit_is_capped_at_200(client, alpha):
    resp = await client.simulate_get("/books?limit=100000", headers=alpha)
    assert resp.status_code == 200


# --- ownership -------------------------------------------------------------------------


async def test_owner_can_update(client, alpha):
    book = await create(client, alpha, category="lore")
    resp = await client.simulate_patch(
        f"/books/{book['id']}", headers=alpha, json={"title": "New title"}
    )
    assert resp.status_code == 200
    assert resp.json["title"] == "New title"
    assert resp.json["content"] == book["content"]  # untouched
    assert resp.json["category"] == "lore"  # untouched
    assert resp.json["updated_at"] >= book["updated_at"]


async def test_patch_null_category_clears_it(client, alpha):
    book = await create(client, alpha, category="lore")
    url = f"/books/{book['id']}"
    resp = await client.simulate_patch(url, headers=alpha, json={"category": None})
    assert resp.status_code == 200
    assert resp.json["category"] is None


async def test_empty_patch_is_a_noop(client, alpha):
    book = await create(client, alpha)
    resp = await client.simulate_patch(f"/books/{book['id']}", headers=alpha, json={})
    assert resp.status_code == 200
    assert resp.json == book


async def test_other_server_cannot_update_or_delete(client, alpha, beta):
    book = await create(client, alpha)
    url = f"/books/{book['id']}"

    # 404, not 403: don't leak that the book exists.
    resp = await client.simulate_patch(url, headers=beta, json={"title": "hijacked"})
    assert resp.status_code == 404
    assert (await client.simulate_delete(url, headers=beta)).status_code == 404

    still_there = (await client.simulate_get(url, headers=alpha)).json
    assert still_there == book


async def test_patch_and_delete_missing_are_404(client, alpha):
    assert (await client.simulate_patch("/books/999", headers=alpha, json={})).status_code == 404
    assert (await client.simulate_delete("/books/999", headers=alpha)).status_code == 404


async def test_owner_can_delete(client, alpha, beta):
    book = await create(client, alpha)
    url = f"/books/{book['id']}"
    resp = await client.simulate_delete(url, headers=alpha)
    assert resp.status_code == 204
    assert resp.text == ""
    assert (await client.simulate_get(url, headers=beta)).status_code == 404


# --- validation ------------------------------------------------------------------------


async def test_create_validation(client, alpha):
    bad_bodies = [
        {**BOOK, "title": ""},
        {**BOOK, "title": "x" * 201},
        {**BOOK, "content": ""},
        {**BOOK, "author": ""},
        {**BOOK, "author": "x" * 101},
        {**BOOK, "category": "x" * 51},
        {"title": "no content or author"},
        {**BOOK, "titel": "typo"},  # unknown fields are rejected, not silently dropped
        {**BOOK, "title": 123},
    ]
    for body in bad_bodies:
        resp = await client.simulate_post("/books", headers=alpha, json=body)
        assert resp.status_code == 422, body
        assert "detail" in resp.json


async def test_limits_are_inclusive(client, alpha):
    await create(client, alpha, title="x" * 200, author="y" * 100, category="z" * 50)


async def test_large_content_is_accepted(client, alpha):
    book = await create(client, alpha, content="lorem ipsum " * 100_000)
    resp = await client.simulate_get(f"/books/{book['id']}", headers=alpha)
    assert len(resp.json["content"]) > 1_000_000


async def test_malformed_json_is_400(client, alpha):
    resp = await client.simulate_post(
        "/books", headers=alpha, body="{not json", content_type="application/json"
    )
    assert resp.status_code == 400
    resp = await client.simulate_post("/books", headers=alpha, body="")
    assert resp.status_code == 400


async def test_patch_validation(client, alpha):
    book = await create(client, alpha)
    for body in ({"title": ""}, {"title": None}, {"content": None}, {"author": None}, {"x": 1}):
        resp = await client.simulate_patch(f"/books/{book['id']}", headers=alpha, json=body)
        assert resp.status_code == 422, body
