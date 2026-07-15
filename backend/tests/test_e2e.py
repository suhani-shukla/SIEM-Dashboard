"""
FILE LOCATION: backend/tests/test_e2e.py

Full pipeline integration test: for each attack type, run the simulation
(fast mode) against the real app in-process, then query the alerts API and
assert the correct playbook fired with the correct MITRE technique.

ASSUMPTIONS:
- conftest.py provides an `app` fixture (the FastAPI application instance)
  and a `client` fixture for making requests against it.
- The rule engine's Redis pub/sub consumer (Phase 2) is actually running
  against the same Redis instance the test app uses — if your test setup
  uses a separate/mocked Redis for other unit tests (e.g. fakeredis in
  test_rules.py), these e2e tests need the REAL redis + a running engine
  worker, since this test intentionally exercises the whole pipeline rather
  than mocking it. Run these against `docker compose` services, not fakeredis.
- Playbook `name` fields match: brute_force_detection, dns_tunneling,
  phishing_detection, privilege_escalation_detection — adjust the
  EXPECTED map below if your playbooks/*.yaml use different `name:` values.

NOTE ON FIXTURE OVERRIDES BELOW:
conftest.py's `redis_client` and `mock_rule_engine_start` fixtures are
autouse=True and are tuned for the *unit* tests (FakeRedis, no real engine
loop). This file locally redefines both so that, for e2e tests only:
  - `redis_client` returns the REAL redis client (so the RuleEngine's
    pub/sub consumer and the app share the same Redis instance the
    simulation writes events into).
  - `mock_rule_engine_start` is a no-op override that does NOT monkeypatch
    RuleEngine.start, so the real engine actually starts and consumes
    events from `events:raw`.
Pytest resolves fixtures by nearest scope, so these definitions shadow the
conftest.py ones only within this module; other test files are unaffected.
"""
import asyncio

import httpx
import pytest
import pytest_asyncio

from app.core import redis as redis_core
from app.simulation.runner import run_simulation

# attack_type -> (expected rule_name substring, expected mitre technique)
EXPECTED = {
    "brute_force": ("brute_force", "T1110"),
    "dns_tunneling": ("dns_tunneling", "T1071.004"),
    "phishing": ("phishing", "T1566"),
    "privilege_escalation": ("privilege_escalation", "T1078"),
}

# Correlation isn't guaranteed to be synchronous with ingestion (the rule
# engine consumes from a pub/sub channel), so poll briefly rather than
# asserting immediately after sending events.
POLL_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 0.5


@pytest_asyncio.fixture
async def redis_client():
    """Override conftest's FakeRedis version — e2e needs the real Redis
    instance so the RuleEngine's pub/sub consumer actually sees events
    published by the simulation/ingestion path."""
    client = await redis_core.get_redis_client()
    yield client


@pytest.fixture(autouse=True)
def mock_rule_engine_start():
    """Override conftest's no-op — e2e needs the real RuleEngine.start()
    loop running so alerts are actually produced."""
    yield


async def _wait_for_alert(client: httpx.AsyncClient, mitre_substring: str):
    elapsed = 0.0
    while elapsed < POLL_TIMEOUT_SECONDS:
        resp = await client.get("/api/v1/alerts", params={"limit": 50})
        resp.raise_for_status()
        items = resp.json()["items"]
        for alert in items:
            technique = alert.get("mitre_technique") or ""
            if mitre_substring in technique:
                return alert
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
    return None


class TestEndToEndSimulations:
    @pytest.mark.parametrize("attack_type", list(EXPECTED.keys()))
    async def test_simulation_produces_correct_alert(self, attack_type, app, client):
        rule_substring, mitre_substring = EXPECTED[attack_type]

        # Run the simulation in-process against the real app via ASGI transport
        # so no real network hop / separate server process is required.
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as sim_client:
            summary = await run_simulation(
                attack_type=attack_type,
                mode="fast",
                noise_events=10,
                seed=1234,
                http_client=sim_client,
            )

        assert summary["events_sent"] > 0

        alert = await _wait_for_alert(client, mitre_substring)
        assert alert is not None, (
            f"Expected an alert with MITRE technique containing '{mitre_substring}' "
            f"after simulating '{attack_type}', but none appeared within "
            f"{POLL_TIMEOUT_SECONDS}s"
        )
        assert rule_substring in alert["rule_name"]

    async def test_run_all_produces_four_alerts(self, app, client):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as sim_client:
            summary = await run_simulation(
                attack_type="all",
                mode="fast",
                noise_events=5,
                seed=999,
                http_client=sim_client,
            )

        assert summary["attack_type"] == "all"
        assert len(summary["attacks_run"]) == 4

        found_techniques = set()
        elapsed = 0.0
        while elapsed < POLL_TIMEOUT_SECONDS and len(found_techniques) < 4:
            resp = await client.get("/api/v1/alerts", params={"limit": 100})
            items = resp.json()["items"]
            for alert in items:
                technique = alert.get("mitre_technique") or ""
                for _, mitre_substring in EXPECTED.values():
                    if mitre_substring in technique:
                        found_techniques.add(mitre_substring)
            if len(found_techniques) >= 4:
                break
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

        expected_techniques = {m for _, m in EXPECTED.values()}
        assert found_techniques == expected_techniques, (
            f"Expected alerts for all of {expected_techniques}, only found {found_techniques}"
        )