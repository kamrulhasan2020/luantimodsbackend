import falcon.asgi
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings, load_settings
from app.db import create_engine
from app.http import error_serializer
from app.middleware import AuthMiddleware, EngineLifespan
from app.rate_limit import RateLimiter
from app.repositories.books import BookRepository
from app.repositories.servers import ServerRepository
from app.resources.books import BOOK_ID_URI, BookResource, BooksResource
from app.resources.health import HealthResource


def create_app(settings: Settings, engine: AsyncEngine | None = None) -> falcon.asgi.App:
    engine = engine or create_engine(settings.database_url)
    books = BookRepository(engine)

    app = falcon.asgi.App(
        middleware=[
            EngineLifespan(engine),
            AuthMiddleware(ServerRepository(engine), RateLimiter(settings.rate_limit_per_minute)),
        ]
    )
    app.set_error_serializer(error_serializer)

    app.add_route("/health", HealthResource(engine))
    app.add_route("/books", BooksResource(books))
    app.add_route(f"/books/{BOOK_ID_URI}", BookResource(books))
    return app


app = create_app(load_settings())
