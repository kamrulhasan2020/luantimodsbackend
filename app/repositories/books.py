from typing import Any

from sqlalchemy import Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.schemas import BookRead, BookSummary
from app.tables import books, servers

MAX_LIMIT = 200

_SERVERNAME = servers.c.name.label("servername")
_READ_COLUMNS = (
    books.c.id,
    books.c.title,
    books.c.content,
    books.c.author,
    books.c.category,
    _SERVERNAME,
    books.c.created_at,
    books.c.updated_at,
)
_SUMMARY_COLUMNS = (
    books.c.id,
    books.c.title,
    books.c.author,
    books.c.category,
    _SERVERNAME,
    books.c.created_at,
)


def _with_server(*columns: Any) -> Select:
    return select(*columns).select_from(books.join(servers, books.c.server_id == servers.c.id))


async def _fetch(conn: AsyncConnection, book_id: int) -> BookRead | None:
    row = (
        await conn.execute(_with_server(*_READ_COLUMNS).where(books.c.id == book_id))
    ).one_or_none()
    return BookRead(**row._mapping) if row else None


class BookRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def create(self, server_id: int, **fields: Any) -> BookRead:
        async with self.engine.begin() as conn:
            result = await conn.execute(
                books.insert().values(server_id=server_id, **fields).returning(books.c.id)
            )
            book = await _fetch(conn, result.scalar_one())
        assert book is not None
        return book

    async def list_all(
        self,
        author: str | None = None,
        category: str | None = None,
        servername: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BookSummary]:
        query = _with_server(*_SUMMARY_COLUMNS)
        if servername is not None:
            query = query.where(servers.c.name == servername)
        if author is not None:
            query = query.where(books.c.author == author)
        if category is not None:
            query = query.where(books.c.category == category)
        query = (
            query.order_by(books.c.created_at.desc(), books.c.id.desc())
            .limit(min(limit, MAX_LIMIT))
            .offset(offset)
        )

        async with self.engine.connect() as conn:
            rows = (await conn.execute(query)).all()
        return [BookSummary(**row._mapping) for row in rows]

    async def get_by_id(self, book_id: int) -> BookRead | None:
        async with self.engine.connect() as conn:
            return await _fetch(conn, book_id)

    async def update(self, book_id: int, server_id: int, **fields: Any) -> BookRead | None:
        """Update a book only if it belongs to `server_id`. None if missing or not theirs."""
        owned = (books.c.id == book_id, books.c.server_id == server_id)
        async with self.engine.begin() as conn:
            if fields:
                result = await conn.execute(update(books).where(*owned).values(**fields))
                found = result.rowcount > 0
            else:
                found = await conn.scalar(select(books.c.id).where(*owned)) is not None
            return await _fetch(conn, book_id) if found else None

    async def delete(self, book_id: int, server_id: int) -> bool:
        """Delete a book only if it belongs to `server_id`. False if missing or not theirs."""
        async with self.engine.begin() as conn:
            result = await conn.execute(
                delete(books).where(books.c.id == book_id, books.c.server_id == server_id)
            )
        return result.rowcount > 0
