import math

import falcon
from sqlalchemy.ext.asyncio import AsyncEngine

from app.rate_limit import RateLimiter
from app.repositories.servers import ServerRepository
from app.security import hash_api_key


class EngineLifespan:
    """Closes the DB connection pool on shutdown."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def process_shutdown(self, scope, event) -> None:
        await self.engine.dispose()


class AuthMiddleware:
    """Authenticates `X-API-Key` and rate limits.

    Authenticated requests are limited per server; failed ones are limited per IP so
    bad-key floods can't hammer the database. Resources opt out with `requires_auth = False`.
    """

    def __init__(self, servers: ServerRepository, limiter: RateLimiter) -> None:
        self.servers = servers
        self.limiter = limiter

    async def process_resource(self, req, resp, resource, params) -> None:
        if resource is None or not getattr(resource, "requires_auth", True):
            return

        api_key = req.get_header("X-API-Key")
        server = await self.servers.get_by_api_key_hash(hash_api_key(api_key)) if api_key else None

        if server is None:
            self._enforce_limit(f"ip:{req.remote_addr}")
            raise falcon.HTTPUnauthorized(
                description="Invalid or missing API key", challenges=["API-Key"]
            )

        self._enforce_limit(f"server:{server.id}")
        req.context.server = server

    def _enforce_limit(self, key: str) -> None:
        retry_after = self.limiter.check(key)
        if retry_after is not None:
            raise falcon.HTTPTooManyRequests(
                description="Rate limit exceeded", retry_after=max(math.ceil(retry_after), 1)
            )
