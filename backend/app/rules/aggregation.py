from __future__ import annotations

from app.rules.base import Alert, Rule, coerce_datetime, matches_criteria, resolve_field


class AggregationRule(Rule):
    def __init__(self, config: dict):
        super().__init__(config)
        self.match_criteria = config.get("match", {})
        self.group_by = config.get("group_by", "source")
        self.aggregate_field = config.get("aggregate_field")
        self.threshold = int(config.get("threshold", 1))
        self.window_seconds = int(config.get("window_seconds", 60))

    async def evaluate(self, event: dict, redis_client) -> Alert | None:
        if not matches_criteria(event, self.match_criteria):
            return None

        event_timestamp = coerce_datetime(event["timestamp"])
        group_value = str(resolve_field(event, self.group_by) or "global")
        aggregate_value = resolve_field(event, self.aggregate_field) if self.aggregate_field else None
        if aggregate_value is None:
            return None

        key = f"aggregation:{self.rule_name}:{group_value}"
        event_key = f"{key}:event_ids"
        cooldown_key = f"{key}:cooldown"

        if await redis_client.exists(cooldown_key):
            return None

        await redis_client.sadd(key, str(aggregate_value))
        await redis_client.sadd(event_key, str(event["id"]))
        await redis_client.expire(key, self.window_seconds)
        await redis_client.expire(event_key, self.window_seconds)

        distinct_count = await redis_client.scard(key)
        if distinct_count < self.threshold:
            return None

        matched_event_ids = sorted(await redis_client.smembers(event_key))
        await redis_client.delete(key)
        await redis_client.delete(event_key)
        await redis_client.setex(cooldown_key, self.window_seconds, str(event["id"]))

        return Alert(
            rule_name=self.rule_name,
            mitre_technique=self.mitre_technique,
            severity=self.severity,
            triggered_at=event_timestamp,
            matched_events=[str(value) for value in matched_event_ids],
            summary=f"{self.rule_name} observed {distinct_count} distinct {self.aggregate_field} values for {group_value}",
            entity=group_value,
        )