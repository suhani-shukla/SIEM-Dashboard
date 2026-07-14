"""
FILE LOCATION: backend/tests/test_alerts.py

Phase 4 tests. Assumes conftest.py already provides:
  - `client`: an httpx.AsyncClient / TestClient against the FastAPI app
  - `db_session`: an async SQLAlchemy session fixture
  - a way to insert a test Alert row directly (adjust `make_alert` helper below
    to match however your existing test_rules.py / test_playbooks.py create
    fixtures, so you're not duplicating setup logic)

These are written as async tests (pytest-asyncio). Add
`asyncio_mode = auto` to pytest.ini if not already set, or mark tests with
@pytest.mark.asyncio individually.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

import pytest

from app.models.alert import Alert


async def make_alert(db_session, status="new", **overrides):
    alert = Alert(
        id=uuid.uuid4(),
        rule_name=overrides.get("rule_name", "brute_force_detection"),
        mitre_technique=overrides.get("mitre_technique", "T1110"),
        severity=overrides.get("severity", "high"),
        triggered_at=datetime.now(timezone.utc),
        matched_event_ids=overrides.get("matched_event_ids", []),
        summary=overrides.get("summary", "test alert"),
        entity=overrides.get("entity", "10.0.0.5"),
        status=status,
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    return alert


class TestAlertTransitions:
    async def test_valid_transition_new_to_acknowledged(self, client, db_session):
        alert = await make_alert(db_session, status="new")
        resp = await client.patch(
            f"/api/v1/alerts/{alert.id}/status",
            json={"status": "acknowledged", "changed_by": "analyst1"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "acknowledged"

    async def test_invalid_transition_new_to_resolved_rejected(self, client, db_session):
        alert = await make_alert(db_session, status="new")
        resp = await client.patch(
            f"/api/v1/alerts/{alert.id}/status",
            json={"status": "resolved", "changed_by": "analyst1"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "invalid_transition"

    async def test_reopen_resolved_alert_allowed(self, client, db_session):
        alert = await make_alert(db_session, status="resolved")
        resp = await client.patch(
            f"/api/v1/alerts/{alert.id}/status",
            json={"status": "investigating", "changed_by": "analyst2", "note": "reopening"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "investigating"

    async def test_history_recorded(self, client, db_session):
        alert = await make_alert(db_session, status="new")
        await client.patch(
            f"/api/v1/alerts/{alert.id}/status",
            json={"status": "acknowledged", "changed_by": "analyst1"},
        )
        detail = await client.get(f"/api/v1/alerts/{alert.id}")
        history = detail.json()["history"]
        assert len(history) == 1
        assert history[0]["from_status"] == "new"
        assert history[0]["to_status"] == "acknowledged"
        assert history[0]["changed_by"] == "analyst1"

    async def test_nonexistent_alert_404(self, client):
        resp = await client.patch(
            f"/api/v1/alerts/{uuid.uuid4()}/status",
            json={"status": "acknowledged", "changed_by": "analyst1"},
        )
        assert resp.status_code == 404


class TestAlertPagination:
    async def test_pagination_no_duplicates_or_gaps(self, client, db_session):
        for i in range(15):
            await make_alert(db_session, entity=f"10.0.0.{i}")

        seen_ids = set()
        offset = 0
        page_size = 5
        while True:
            resp = await client.get(f"/api/v1/alerts?limit={page_size}&offset={offset}")
            body = resp.json()
            items = body["items"]
            if not items:
                break
            for item in items:
                assert item["id"] not in seen_ids, "duplicate alert across pages"
                seen_ids.add(item["id"])
            offset += page_size
            if offset >= body["total"]:
                break

        assert len(seen_ids) == 15

    async def test_filter_by_status(self, client, db_session):
        await make_alert(db_session, status="new")
        await make_alert(db_session, status="resolved")
        resp = await client.get("/api/v1/alerts?status=resolved")
        body = resp.json()
        assert all(item["status"] == "resolved" for item in body["items"])


class TestAlertSSE:
    async def test_sse_receives_published_alert(self, client, redis_client):
        received = asyncio.Event()
        payload = {"id": str(uuid.uuid4()), "rule_name": "brute_force_detection"}

        async def consume():
            try:
                async with client.stream("GET", "/api/v1/alerts/stream") as response:
                    print(f"DEBUG SSE: status={response.status_code}")
                    async for line in response.aiter_lines():
                        print(f"DEBUG SSE: line={line}")
                        if line.startswith("data:"):
                            data = json.loads(line[len("data:"):].strip())
                            if data.get("id") == payload["id"]:
                                received.set()
                                break
            except Exception as e:
                print(f"DEBUG SSE: exception={e}")

        consumer_task = asyncio.create_task(consume())
        await asyncio.sleep(0.2)  # let the subscription establish
        await redis_client.publish("alerts:new", json.dumps(payload))

        await asyncio.wait_for(received.wait(), timeout=5)
        consumer_task.cancel()