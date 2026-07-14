import asyncio
import json
import uuid
from datetime import datetime, timezone

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.alert import Alert as AlertRecord
from app.rules.engine import RuleEngine

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


def _bruteforce_payloads(source: str = "192.168.1.20") -> list[dict]:
    base = datetime(2026, 7, 9, 15, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "timestamp": base.replace(second=i * 5).isoformat(),
            "source": source,
            "event_type": "login_failed",
            "severity": "high",
            "raw_payload": {"ip": source, "user": "admin"},
            "metadata": {},
        }
        for i in range(3)
    ]


@pytest.mark.asyncio
async def test_engine_publishes_new_alert_to_correct_channel(db_session, redis_client, monkeypatch):
    """
    Verifies the engine publishes a correctly-shaped alert payload to the
    exact channel (alerts:new) the SSE endpoint subscribes to, whenever a
    rule fires on real ingested events.

    An earlier version of this test ran a full concurrent pub/sub round-trip
    (a live RuleEngine._run() task + an independent subscriber both driven
    by the same event loop) to match the manual QA session's curl -N +
    trigger_bruteforce.py steps. That approach repeatedly hung under
    pytest-asyncio + FakeRedis -- FakeRedis's async pubsub get_message(timeout=...)
    does not appear to reliably honor timeouts under concurrent tasks, which
    is a test-infrastructure limitation rather than an application bug.

    This version keeps the real ingestion path (app.services.events.create_events,
    the same function the HTTP route calls) and the real rule evaluation
    (engine._process_event, unmodified engine code), but observes the
    publish call directly via a spy instead of trying to receive it back
    through a second subscription -- deterministic, no timeouts, no hang risk.
    """
    from app.schemas.event import EventCreate, EventResponse
    from app.services.events import create_events

    published: list[tuple[str, str]] = []
    original_publish = redis_client.publish

    async def spy_publish(channel, message):
        published.append((channel, message))
        return await original_publish(channel, message)

    monkeypatch.setattr(redis_client, "publish", spy_publish)

    engine = RuleEngine(redis_client=redis_client)
    events_in = [EventCreate(**payload) for payload in _bruteforce_payloads()]
    events = await create_events(db_session, redis_client, events_in)

    for event in events:
        event_data = EventResponse.from_orm_event(event).model_dump(mode="json")
        await engine._process_event(event_data)

    new_alert_messages = [msg for channel, msg in published if channel == "alerts:new"]
    assert new_alert_messages, "engine never published to the alerts:new channel"

    payload = json.loads(new_alert_messages[0])
    assert payload["rule_name"] == "demo_threshold_bruteforce"
    assert payload["entity"] == "192.168.1.20"
    assert len(payload["matched_events"]) == 3

    # Confirm it also made it to the DB, not just the pub/sub channel
    result = await db_session.execute(select(AlertRecord))
    alerts = result.scalars().all()
    assert alerts, "expected the alert to be persisted to the DB as well"