from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.tables import servers, utcnow


class ServerExistsError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Server:
    id: int
    name: str
    email: str | None
    has_api_key: bool
    api_key_created_at: datetime | None
    created_at: datetime


_COLUMNS = (
    servers.c.id,
    servers.c.name,
    servers.c.email,
    servers.c.api_key_hash.is_not(None).label("has_api_key"),
    servers.c.api_key_created_at,
    servers.c.created_at,
)


class ServerRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def get_by_api_key_hash(self, api_key_hash: str) -> Server | None:
        async with self.engine.connect() as conn:
            row = (
                await conn.execute(select(*_COLUMNS).where(servers.c.api_key_hash == api_key_hash))
            ).one_or_none()
        return Server(**row._mapping) if row else None

    async def list_all(self) -> list[Server]:
        async with self.engine.connect() as conn:
            rows = (await conn.execute(select(*_COLUMNS).order_by(servers.c.name))).all()
        return [Server(**row._mapping) for row in rows]

    async def create(self, name: str, email: str | None, api_key_hash: str) -> None:
        now = utcnow()
        try:
            async with self.engine.begin() as conn:
                await conn.execute(
                    servers.insert().values(
                        name=name,
                        email=email,
                        api_key_hash=api_key_hash,
                        api_key_created_at=now,
                    )
                )
        except IntegrityError as exc:
            raise ServerExistsError(name) from exc

    async def set_api_key_hash(self, name: str, api_key_hash: str | None) -> bool:
        """Set (rotate) or clear (revoke, with None) a server's key. False if no such server."""
        async with self.engine.begin() as conn:
            result = await conn.execute(
                update(servers)
                .where(servers.c.name == name)
                .values(
                    api_key_hash=api_key_hash,
                    api_key_created_at=utcnow() if api_key_hash else None,
                )
            )
        return result.rowcount > 0
