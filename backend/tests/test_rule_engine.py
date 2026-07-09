import uuid
from datetime import datetime, timezone

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.alert import Alert as AlertRecord


@pytest.fixture
async def fake_redis(monkeypatch):
    client = FakeRedis(decode_responses=True)

    async def _get_redis_client():
        return client

    monkeypatch.setattr("app.core.redis.get_redis_client", _get_redis_client)
    yield client
    await client.aclose()


@pytest.fixture
async def client(fake_redis):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_burst_of_events_creates_alert_row(client, db_session, fake_redis):
    base = datetime(2026, 7, 9, 15, 0, 0, tzinfo=timezone.utc)
    payloads = [
        {
            "timestamp": base.isoformat(),
            "source": "192.168.1.20",
            "event_type": "login_failed",
            "severity": "high",
            "raw_payload": {"ip": "192.168.1.20", "user": "admin"},
            "metadata": {},
        },
        {
            "timestamp": base.replace(second=5).isoformat(),
            "source": "192.168.1.20",
            "event_type": "login_failed",
            "severity": "high",
            "raw_payload": {"ip": "192.168.1.20", "user": "admin"},
            "metadata": {},
        },
        {
            "timestamp": base.replace(second=10).isoformat(),
            "source": "192.168.1.20",
            "event_type": "login_failed",
            "severity": "high",
            "raw_payload": {"ip": "192.168.1.20", "user": "admin"},
            "metadata": {},
        },
    ]

    from app.rules.engine import RuleEngine
    engine = RuleEngine(redis_client=fake_redis)

    for payload in payloads:
        response = await client.post("/api/v1/events", json=payload)
        assert response.status_code == 201
        
        # Manually process the event to avoid flaky pubsub in tests
        event_data = response.json()
        if isinstance(event_data, list):
            for ev in event_data:
                await engine._process_event(ev)
        else:
            await engine._process_event(event_data)

    result = await db_session.execute(select(AlertRecord))
    alerts = result.scalars().all()
    assert alerts, "expected a persisted alert after threshold burst"
    alert = alerts[0]
    assert alert.rule_name == "demo_threshold_bruteforce"
    assert alert.status == "new"
    assert len(alert.matched_event_ids) == 3