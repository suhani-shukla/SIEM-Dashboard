from __future__ import annotations

import asyncio
import json
import logging

from redis.asyncio import Redis

from app.core.redis import EVENTS_RAW_CHANNEL
from app.db.session import async_session_factory
from app.models.alert import Alert as AlertRecord
from app.rules.aggregation import AggregationRule
from app.rules.base import Alert, alert_to_record_kwargs
from app.rules.sequence import SequenceRule
from app.rules.threshold import ThresholdRule

logger = logging.getLogger("rule_engine")

ALERTS_NEW_CHANNEL = "alerts:new"


def build_default_rules() -> list:
    return [
        ThresholdRule(
            {
                "rule_name": "demo_threshold_bruteforce",
                "mitre_technique": "T1110",
                "severity": "high",
                "match": {"event_type": "login_failed", "severity": "high"},
                "count": 3,
                "window_seconds": 60,
                "group_by": "source",
            }
        ),
        SequenceRule(
            {
                "rule_name": "demo_sequence_privilege_escalation",
                "mitre_technique": "T1068",
                "severity": "critical",
                "steps": [
                    {"event_type": "login_failed"},
                    {"event_type": "login_success"},
                    {"event_type": "privilege_escalation"},
                ],
                "window_seconds": 300,
                "group_by": "source",
            }
        ),
        AggregationRule(
            {
                "rule_name": "demo_aggregation_dns_tunnel",
                "mitre_technique": "T1071.004",
                "severity": "medium",
                "match": {"event_type": "dns_query"},
                "group_by": "source",
                "aggregate_field": "raw_payload.destination_ip",
                "threshold": 5,
                "window_seconds": 120,
            }
        ),
    ]


class RuleEngine:
    def __init__(self, redis_client: Redis, rules: list | None = None):
        self.redis_client = redis_client
        self.rules = rules or build_default_rules()
        self._task: asyncio.Task | None = None

    def update_rules(self, rules: list) -> None:
        self.rules = rules

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            logger.info("RuleEngine started with %d rules", len(self.rules))

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(self) -> None:
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(EVENTS_RAW_CHANNEL)
        logger.info("RuleEngine subscribed to %s", EVENTS_RAW_CHANNEL)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    await asyncio.sleep(0.05)
                    continue
                if message.get("type") != "message":
                    continue
                payload = message.get("data")
                if not payload:
                    continue
                try:
                    event = json.loads(payload)
                    await self._process_event(event)
                except Exception:
                    logger.exception("Failed to process event: %r", payload)
        finally:
            await pubsub.unsubscribe(EVENTS_RAW_CHANNEL)
            await pubsub.aclose()
            logger.info("RuleEngine stopped")

    async def _process_event(self, event: dict) -> None:
        for rule in self.rules:
            logger.info(
                "Evaluating rule=%s match=%s against event=%s",
                rule.rule_name,
                getattr(rule, "match_criteria", None),
                event,
            )
            alert = await rule.evaluate(event, self.redis_client)
            if alert is None:
                logger.info("Rule %s did not fire", rule.rule_name)
                continue
            logger.info("Rule %s fired: %s", rule.rule_name, alert.summary)
            await self._persist_alert(alert)

    async def _persist_alert(self, alert: Alert) -> None:
        async with async_session_factory() as session:
            session.add(AlertRecord(**alert_to_record_kwargs(alert)))
            await session.commit()
        try:
            await self.redis_client.publish(ALERTS_NEW_CHANNEL, alert.model_dump_json())
        except Exception:
            logger.exception("Failed to publish alert %s to %s", alert.id, ALERTS_NEW_CHANNEL)