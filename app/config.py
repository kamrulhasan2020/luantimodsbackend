import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    # Async SQLAlchemy URL. SQLite for now; Postgres later would be
    # postgresql+asyncpg://user:password@host:5432/dbname (and add asyncpg as a dependency).
    database_url: str = "sqlite+aiosqlite:///./data/db.sqlite3"
    # Requests per minute allowed per API key (and per IP for unauthenticated requests).
    rate_limit_per_minute: int = 60


def load_settings() -> Settings:
    defaults = Settings()
    return Settings(
        database_url=os.environ.get("DATABASE_URL", defaults.database_url),
        rate_limit_per_minute=int(
            os.environ.get("RATE_LIMIT_PER_MINUTE", defaults.rate_limit_per_minute)
        ),
    )
