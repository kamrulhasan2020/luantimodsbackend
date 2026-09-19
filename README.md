# Luanti Mods Backend

Shared in-game book library for Luanti (Minetest) servers. Game servers create books on
behalf of their players; every registered server can read every book, but only the server
that created a book can change or delete it.

## Stack

- **Falcon** (ASGI) + **msgspec** for request/response validation and JSON
- **SQLAlchemy Core** (async) on **SQLite** via `aiosqlite`, **Alembic** for migrations
- **Granian** as the ASGI server
- **uv** for dependencies, **Docker** (multistage: `dev` with hot reload, `prod` non-root)

## Running locally

```bash
uv sync
uv run alembic upgrade head
uv run granian --interface asgi --workers 1 --reload app.main:app
```

Health check: `GET http://localhost:8000/health`

With Docker (hot reload, code bind-mounted, DB persisted in `./data/`):

```bash
docker compose up --build
```

Configuration is via environment variables (see `.env.example`; all optional):
`DATABASE_URL` and `RATE_LIMIT_PER_MINUTE`.

## Servers and API keys

There is no login and no self-service key generation yet. A server owner is registered by
hand and sent their key (e.g. by email):

```bash
uv run python -m app.cli create-server myserver --email owner@example.com   # prints the key once
uv run python -m app.cli rotate-key myserver    # new key, old one stops working
uv run python -m app.cli revoke-key myserver    # server can no longer call the API
uv run python -m app.cli list-servers
```

In Docker: `docker compose exec web python -m app.cli create-server myserver`.

Only a SHA-256 hash of each key is stored, so a key can never be shown again — rotate if
it's lost. Each server has one key at a time.

## API

Every endpoint except `/health` requires an `X-API-Key` header. Errors are always
`{"detail": "..."}`.

| Endpoint             | Description |
|----------------------|-------------|
| `POST /books`        | Create a book (`title`, `content`, `author`, optional `category`), owned by the calling server. `201` |
| `GET /books`         | List books from all servers, newest first. Lightweight items (no `content`). Filters: `author`, `category`, `server`. Paging: `limit` (default 50, max 200), `offset` |
| `GET /books/{id}`    | Any book, full detail |
| `PATCH /books/{id}`  | Partial update. Only the creating server. `"category": null` clears the category |
| `DELETE /books/{id}` | Only the creating server. `204` |

Field limits: `title` 1–200 chars, `author` 1–100, `category` up to 50, `content` non-empty
(no upper bound). Unknown fields are rejected.

Status codes: `400` malformed JSON or bad query params, `401` missing/invalid key,
`404` missing book *or* someone else's book on `PATCH`/`DELETE` (so existence isn't leaked),
`422` validation failure, `429` rate limited (with `Retry-After`).

### Access model

The API only knows about **servers**, not players. `author` is just a string the game
server sends; it is never checked against a real player identity. Any request signed with
the creating server's key may modify that server's books.

So the in-game mod must verify that the acting player is the book's `author` **before**
calling `PATCH`/`DELETE` — from this API's point of view that is indistinguishable from the
server itself acting.

## Rate limiting

60 requests/minute per API key (configurable). Requests with a missing or bad key are
limited per client IP instead, so they can't be used to hammer the database. `/health` is
exempt. Over the limit returns `429` with a `Retry-After` header.

The limiter is in-memory, so it's only accurate within one process — that's why Granian
runs with `--workers 1`. Move it to a shared store (e.g. Redis) before scaling past one
worker. Behind a reverse proxy, the client IP is the proxy's unless it's configured to
forward the real one.

## Migrations

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

The Docker entrypoint runs `alembic upgrade head` on every start.

## Tests

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Layout

```
app/
  main.py            # create_app() + the `app` Granian serves
  config.py          # env-based settings
  tables.py          # SQLAlchemy Core table definitions
  db.py              # async engine (SQLite pragmas)
  schemas.py         # msgspec request/response structs
  middleware.py      # API-key auth + rate limiting
  rate_limit.py      # sliding-window limiter
  resources/         # Falcon resources (health, books)
  repositories/      # DB access (books, servers)
  cli.py             # server/key management
alembic/             # migrations
tests/
```
