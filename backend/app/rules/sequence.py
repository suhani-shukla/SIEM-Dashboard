from __future__ import annotations

import json

from app.rules.base import Alert, Rule, coerce_datetime, matches_criteria, resolve_field


class SequenceRule(Rule):
    def __init__(self, config: dict):
        super().__init__(config)
        self.steps = config.get("steps", [])
        self.window_seconds = int(config.get("window_seconds", 60))
        self.group_by = config.get("group_by", "source")

    async def evaluate(self, event: dict, redis_client) -> Alert | None:
        if not self.steps:
            return None

        event_timestamp = coerce_datetime(event["timestamp"])
        group_value = str(resolve_field(event, self.group_by) or "global")
        key = f"sequence:{self.rule_name}:{group_value}"

        state = await redis_client.hgetall(key)
        step_index = int(state.get("step_index", 0) or 0)
        first_ts_raw = state.get("first_ts")
        matched_event_ids = json.loads(state.get("matched_event_ids", "[]"))

        if first_ts_raw:
            first_ts = coerce_datetime(first_ts_raw)
            if (event_timestamp - first_ts).total_seconds() > self.window_seconds:
                await redis_client.delete(key)
                state = {}
                step_index = 0
                matched_event_ids = []
        else:
            first_ts = event_timestamp

        current_step = self.steps[step_index] if step_index < len(self.steps) else None
        step_zero = self.steps[0]

        if current_step and matches_criteria(event, current_step):
            if step_index == 0:
                matched_event_ids = [str(event["id"])]
                step_index = 1
                first_ts = event_timestamp
            else:
                matched_event_ids.append(str(event["id"]))
                step_index += 1

            if step_index >= len(self.steps):
                await redis_client.delete(key)
                return Alert(
                    rule_name=self.rule_name,
                    mitre_technique=self.mitre_technique,
                    severity=self.severity,
                    triggered_at=event_timestamp,
                    matched_events=matched_event_ids,
                    summary=f"{self.rule_name} completed ordered sequence for {group_value}",
                    entity=group_value,
                )

            await redis_client.hset(
                key,
                mapping={
                    "step_index": step_index,
                    "first_ts": first_ts.isoformat(),
                    "matched_event_ids": json.dumps(matched_event_ids),
                },
            )
            await redis_client.expire(key, self.window_seconds)
            return None

        if matches_criteria(event, step_zero):
            await redis_client.hset(
                key,
                mapping={
                    "step_index": 1,
                    "first_ts": event_timestamp.isoformat(),
                    "matched_event_ids": json.dumps([str(event["id"])]),
                },
            )
            await redis_client.expire(key, self.window_seconds)

        return None