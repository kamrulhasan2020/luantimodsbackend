from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.http import write_json


class HealthResource:
    requires_auth = False

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def on_get(self, req, resp) -> None:
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        write_json(resp, {"status": "ok"})
