import falcon

from app.http import read_body, write_json
from app.repositories.books import MAX_LIMIT, BookRepository
from app.schemas import BookCreate, BookUpdate

# Book ids are SQLite INTEGERs (signed 64-bit); anything bigger can't exist.
BOOK_ID_URI = "{book_id:int(min=1, max=9223372036854775807)}"


class BooksResource:
    """/books - the library is global: any registered server can read every book."""

    def __init__(self, books: BookRepository) -> None:
        self.books = books

    async def on_post(self, req, resp) -> None:
        body = await read_body(req, BookCreate)
        book = await self.books.create(
            server_id=req.context.server.id,
            title=body.title,
            content=body.content,
            author=body.author,
            category=body.category,
        )
        write_json(resp, book, falcon.HTTP_201)

    async def on_get(self, req, resp) -> None:
        limit = req.get_param_as_int("limit", min_value=1, default=50)
        offset = req.get_param_as_int("offset", min_value=0, default=0)
        result = await self.books.list_all(
            author=req.get_param("author"),
            category=req.get_param("category"),
            servername=req.get_param("server"),
            limit=min(limit, MAX_LIMIT),
            offset=offset,
        )
        write_json(resp, result)


class BookResource:
    """/books/{id} - reads are global; only the creating server may update or delete.

    Mutating someone else's book returns 404 (not 403) so its existence isn't leaked.
    """

    def __init__(self, books: BookRepository) -> None:
        self.books = books

    async def on_get(self, req, resp, book_id: int) -> None:
        book = await self.books.get_by_id(book_id)
        if book is None:
            raise falcon.HTTPNotFound(description="Book not found")
        write_json(resp, book)

    async def on_patch(self, req, resp, book_id: int) -> None:
        body = await read_body(req, BookUpdate)
        book = await self.books.update(book_id, req.context.server.id, **body.changes())
        if book is None:
            raise falcon.HTTPNotFound(description="Book not found")
        write_json(resp, book)

    async def on_delete(self, req, resp, book_id: int) -> None:
        if not await self.books.delete(book_id, req.context.server.id):
            raise falcon.HTTPNotFound(description="Book not found")
        resp.status = falcon.HTTP_204
