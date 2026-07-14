import asyncio
import socket

import pytest
import pytest_asyncio
import sqlalchemy as sa
import uvicorn
from fakeredis.aioredis import FakeRedis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def redis_client(monkeypatch):
    client = FakeRedis(decode_responses=True)

    async def _get_redis_client():
        return client

    monkeypatch.setattr("app.core.redis.get_redis_client", _get_redis_client)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    from app.db.session import async_session_factory
    async with async_session_factory() as session:
        yield session


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest_asyncio.fixture
async def client(redis_client, db_session):
    """
    Runs the app on a real uvicorn server (loopback socket) instead of
    httpx's ASGITransport. ASGITransport runs the app fully in-process and
    cannot deliver an infinite/streaming response (like our SSE feed)
    incrementally — the client just hangs waiting for a body that never
    finishes. A real server, run as a task on this same event loop (so the
    FakeRedis client above stays usable), avoids that.
    """
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="on", log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # not the main thread's job in tests

    server_task = asyncio.create_task(server.serve())

    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.02)
    else:
        server_task.cancel()
        raise RuntimeError("uvicorn test server failed to start")

    async with AsyncClient(base_url=f"http://127.0.0.1:{port}") as ac:
        yield ac

    server.should_exit = True
    await server_task
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_rule_engine_start(monkeypatch):
    async def mock_start(*args, **kwargs):
        pass

    monkeypatch.setattr("app.rules.engine.RuleEngine.start", mock_start)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_database(db_engine):
    yield
    async with db_engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM alert_history"))
        await conn.execute(sa.text("DELETE FROM alerts"))
        await conn.execute(sa.text("DELETE FROM events"))