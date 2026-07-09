import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.alert import Alert as AlertRecord
from app.models.playbook_override import PlaybookOverride
from app.playbooks.loader import load_playbooks
from app.db.session import get_db

from asgi_lifespan import LifespanManager




@pytest.fixture
async def client(fake_redis, db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_playbook_api_list(client):
    response = await client.get("/api/v1/playbooks")
    assert response.status_code == 200
    playbooks = response.json()
    assert len(playbooks) >= 4
    names = [p["name"] for p in playbooks]
    assert "brute_force_detection" in names


@pytest.mark.asyncio
async def test_playbook_api_patch(client, db_session):
    response = await client.patch("/api/v1/playbooks/brute_force_detection", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    result = await db_session.execute(select(PlaybookOverride).where(PlaybookOverride.name == "brute_force_detection"))
    override = result.scalars().first()
    assert override is not None
    assert override.enabled is False


@pytest.mark.asyncio
async def test_brute_force_playbook_fires(client, db_session, fake_redis):
    base = datetime.now(timezone.utc)
    
    # Needs 5 events to fire (playbook threshold is 5)
    payloads = [
        {
            "timestamp": base.isoformat(),
            "source": "10.0.0.1",
            "event_type": "auth_failure",
            "severity": "high",
            "raw_payload": {"source_ip": "10.0.0.1"},
            "metadata": {},
        }
        for _ in range(5)
    ]

    from app.rules.engine import RuleEngine
    # Load actual playbooks to test them
    rules = await load_playbooks(db_session)
    engine = RuleEngine(redis_client=fake_redis, rules=rules)

    for payload in payloads:
        response = await client.post("/api/v1/events", json=payload)
        assert response.status_code == 201
        event_data = response.json()
        await engine._process_event(event_data)

    result = await db_session.execute(select(AlertRecord).where(AlertRecord.rule_name == "brute_force_detection"))
    alerts = result.scalars().all()
    assert alerts, "expected a persisted alert after threshold burst"
    alert = alerts[0]
    assert alert.mitre_technique == "T1110"
