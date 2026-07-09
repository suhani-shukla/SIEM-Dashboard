import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.event import Event

'''
@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

'''


@pytest.fixture(autouse=True)
async def cleanup_events(db_session):
    yield
    await db_session.execute(Event.__table__.delete())
    await db_session.commit()


@pytest.mark.asyncio
async def test_post_event_persisted(client, db_session):
    payload = {
        "timestamp": datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        "source": "test-source",
        "event_type": "login_failed",
        "severity": "high",
        "raw_payload": {"ip": "10.0.0.1", "user": "admin"},
        "metadata": {"test": True},
    }

    response = await client.post("/api/v1/events", json=payload)
    assert response.status_code == 201

    body = response.json()
    assert "id" in body
    assert body["source"] == "test-source"
    assert body["event_type"] == "login_failed"
    assert body["severity"] == "high"
    assert body["raw_payload"] == {"ip": "10.0.0.1", "user": "admin"}
    assert body["metadata"] == {"test": True}

    await db_session.rollback()
    result = await db_session.execute(
        select(Event).where(Event.id == uuid.UUID(body["id"]))
    )
    stored = result.scalar_one()
    assert stored.source == "test-source"
    assert stored.event_type == "login_failed"
    assert stored.severity == "high"
    assert stored.raw_payload == {"ip": "10.0.0.1", "user": "admin"}
    assert stored.event_metadata == {"test": True}
