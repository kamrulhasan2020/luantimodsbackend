from dataclasses import replace

import pytest
from falcon import testing

from app.config import Settings
from app.db import create_engine
from app.main import create_app
from app.repositories.servers import ServerRepository
from app.security import generate_api_key, hash_api_key
from app.tables import metadata


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(database_url=f"sqlite+aiosqlite:///{tmp_path}/test.sqlite3")


@pytest.fixture
async def engine(settings):
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def make_client(settings, engine):
    """Factory so a test can override settings (e.g. a tiny rate limit)."""
    conductors = []

    async def factory(**overrides) -> testing.ASGIConductor:
        app = create_app(replace(settings, **overrides), engine)
        conductor = testing.ASGIConductor(app)
        await conductor.__aenter__()
        conductors.append(conductor)
        return conductor

    yield factory
    for conductor in conductors:
        await conductor.__aexit__(None, None, None)


@pytest.fixture
async def client(make_client) -> testing.ASGIConductor:
    return await make_client()


async def issue_key(engine, name: str) -> dict[str, str]:
    api_key = generate_api_key()
    await ServerRepository(engine).create(name, None, hash_api_key(api_key))
    return {"X-API-Key": api_key}


@pytest.fixture
async def alpha(engine) -> dict[str, str]:
    """Auth headers for server 'alpha'."""
    return await issue_key(engine, "alpha")


@pytest.fixture
async def beta(engine) -> dict[str, str]:
    """Auth headers for server 'beta'."""
    return await issue_key(engine, "beta")


BOOK = {"title": "The Lost Pickaxe", "content": "Once upon a time...", "author": "steve"}
