from __future__ import annotations

from app.rules.base import Alert, Rule, coerce_datetime, matches_criteria, resolve_field


class ThresholdRule(Rule):
    def __init__(self, config: dict):
        super().__init__(config)
        self.match_criteria = config.get("match", {})
        self.count = int(config.get("count", 1))
        self.window_seconds = int(config.get("window_seconds", 60))
        self.group_by = config.get("group_by", "source")

    async def evaluate(self, event: dict, redis_client) -> Alert | None:
        if not matches_criteria(event, self.match_criteria):
            return None

        event_timestamp = coerce_datetime(event["timestamp"])
        group_value = str(resolve_field(event, self.group_by) or "global")
        key = f"threshold:{self.rule_name}:{group_value}"
        cooldown_key = f"{key}:cooldown"

        if await redis_client.exists(cooldown_key):
            return None

        score = event_timestamp.timestamp()
        event_id = str(event["id"])
        await redis_client.zadd(key, {event_id: score})
        await redis_client.zremrangebyscore(key, "-inf", score - self.window_seconds)

        event_ids = await redis_client.zrange(key, 0, -1)
        if len(event_ids) < self.count:
            return None

        await redis_client.delete(key)
        await redis_client.setex(cooldown_key, self.window_seconds, event_id)

        return Alert(
            rule_name=self.rule_name,
            mitre_technique=self.mitre_technique,
            severity=self.severity,
            triggered_at=event_timestamp,
            matched_events=[str(value) for value in event_ids],
            summary=f"{self.rule_name} matched {len(event_ids)} events for {group_value}",
            entity=group_value,
        )