from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.types import TypeDecorator

# Explicit constraint names keep Alembic (especially SQLite batch mode) happy.
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class UTCDateTime(TypeDecorator):
    """Stores naive UTC, always hands back timezone-aware UTC (SQLite drops tzinfo)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None else None


def utcnow() -> datetime:
    return datetime.now(UTC)


servers = Table(
    "servers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column("email", String),
    # SHA-256 of the API key; NULL once revoked. The plaintext key is never stored.
    Column("api_key_hash", String, unique=True),
    Column("api_key_created_at", UTCDateTime),
    Column("created_at", UTCDateTime, nullable=False, default=utcnow),
)

books = Table(
    "books",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "server_id",
        Integer,
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("title", String, nullable=False),
    Column("content", Text, nullable=False),
    Column("author", String, nullable=False, index=True),
    Column("category", String, index=True),
    Column("created_at", UTCDateTime, nullable=False, default=utcnow, index=True),
    Column("updated_at", UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow),
)
