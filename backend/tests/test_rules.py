import uuid
from datetime import datetime, timezone

import pytest
from fakeredis.aioredis import FakeRedis

from app.rules.aggregation import AggregationRule
from app.rules.sequence import SequenceRule
from app.rules.threshold import ThresholdRule


def build_event(
    *,
    event_id: str | None = None,
    timestamp: datetime,
    source: str,
    event_type: str,
    severity: str = "high",
    raw_payload: dict | None = None,
) -> dict:
    return {
        "id": event_id or str(uuid.uuid4()),
        "timestamp": timestamp.isoformat(),
        "source": source,
        "event_type": event_type,
        "severity": severity,
        "raw_payload": raw_payload or {},
        "metadata": {},
    }


@pytest.fixture
async def redis_client():
    client = FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_threshold_rule_fires_on_count_and_resets(redis_client):
    rule = ThresholdRule(
        {
            "rule_name": "threshold-test",
            "mitre_technique": "T1110",
            "severity": "high",
            "match": {"event_type": "login_failed"},
            "count": 3,
            "window_seconds": 10,
            "group_by": "source",
        }
    )
    base = datetime(2026, 7, 9, 12, 0, 0, tzinfo=timezone.utc)

    assert await rule.evaluate(build_event(timestamp=base, source="10.0.0.1", event_type="login_failed"), redis_client) is None
    assert await rule.evaluate(build_event(timestamp=base.replace(second=5), source="10.0.0.1", event_type="login_failed"), redis_client) is None

    alert = await rule.evaluate(build_event(timestamp=base.replace(second=8), source="10.0.0.1", event_type="login_failed"), redis_client)
    assert alert is not None
    assert alert.rule_name == "threshold-test"
    assert alert.entity == "10.0.0.1"
    assert len(alert.matched_events) == 3

    await redis_client.flushdb()
    assert await rule.evaluate(build_event(timestamp=base, source="10.0.0.2", event_type="login_failed"), redis_client) is None
    assert await rule.evaluate(build_event(timestamp=base.replace(second=8), source="10.0.0.2", event_type="login_failed"), redis_client) is None
    assert await rule.evaluate(build_event(timestamp=base.replace(second=21), source="10.0.0.2", event_type="login_failed"), redis_client) is None


@pytest.mark.asyncio
async def test_sequence_rule_fires_only_in_order(redis_client):
    rule = SequenceRule(
        {
            "rule_name": "sequence-test",
            "mitre_technique": "T1068",
            "severity": "critical",
            "steps": [
                {"event_type": "login_failed"},
                {"event_type": "login_success"},
                {"event_type": "privilege_escalation"},
            ],
            "window_seconds": 60,
            "group_by": "source",
        }
    )
    base = datetime(2026, 7, 9, 13, 0, 0, tzinfo=timezone.utc)

    assert await rule.evaluate(build_event(timestamp=base, source="10.0.0.3", event_type="login_failed"), redis_client) is None
    assert await rule.evaluate(build_event(timestamp=base.replace(second=5), source="10.0.0.3", event_type="dns_query"), redis_client) is None
    assert await rule.evaluate(build_event(timestamp=base.replace(second=10), source="10.0.0.3", event_type="login_success"), redis_client) is None

    alert = await rule.evaluate(build_event(timestamp=base.replace(second=15), source="10.0.0.3", event_type="privilege_escalation"), redis_client)
    assert alert is not None
    assert alert.rule_name == "sequence-test"
    assert alert.entity == "10.0.0.3"
    assert len(alert.matched_events) == 3

    await redis_client.flushdb()
    assert await rule.evaluate(build_event(timestamp=base, source="10.0.0.4", event_type="login_success"), redis_client) is None
    assert await rule.evaluate(build_event(timestamp=base.replace(second=5), source="10.0.0.4", event_type="privilege_escalation"), redis_client) is None


@pytest.mark.asyncio
async def test_aggregation_rule_fires_on_distinct_threshold(redis_client):
    rule = AggregationRule(
        {
            "rule_name": "aggregation-test",
            "mitre_technique": "T1071.004",
            "severity": "medium",
            "match": {"event_type": "dns_query"},
            "group_by": "source",
            "aggregate_field": "raw_payload.destination_ip",
            "threshold": 3,
            "window_seconds": 30,
        }
    )
    base = datetime(2026, 7, 9, 14, 0, 0, tzinfo=timezone.utc)

    assert await rule.evaluate(build_event(timestamp=base, source="10.0.0.5", event_type="dns_query", raw_payload={"destination_ip": "1.1.1.1"}), redis_client) is None
    assert await rule.evaluate(build_event(timestamp=base.replace(second=5), source="10.0.0.5", event_type="dns_query", raw_payload={"destination_ip": "2.2.2.2"}), redis_client) is None

    alert = await rule.evaluate(build_event(timestamp=base.replace(second=10), source="10.0.0.5", event_type="dns_query", raw_payload={"destination_ip": "3.3.3.3"}), redis_client)
    assert alert is not None
    assert alert.rule_name == "aggregation-test"
    assert alert.entity == "10.0.0.5"
    assert len(alert.matched_events) == 3