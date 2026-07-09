from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Alert(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    rule_name: str
    mitre_technique: str
    severity: str
    triggered_at: datetime
    matched_events: list[str]
    summary: str
    entity: str
    status: str = "new"

    @field_serializer("triggered_at")
    def serialize_triggered_at(self, value: datetime) -> str:
        return value.isoformat()


class Rule(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.rule_name = config.get("rule_name", self.__class__.__name__)
        self.mitre_technique = config.get("mitre_technique", "unknown")
        self.severity = config.get("severity", "medium")

    @abstractmethod
    async def evaluate(self, event: dict, redis_client) -> Alert | None:
        raise NotImplementedError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def resolve_field(event: dict[str, Any], field_path: str) -> Any:
    if field_path in event:
        return event[field_path]

    current: Any = event
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def matches_criteria(event: dict[str, Any], criteria: dict[str, Any]) -> bool:
    for field, expected in criteria.items():
        if resolve_field(event, field) != expected:
            return False
    return True


def alert_to_record_kwargs(alert: Alert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "rule_name": alert.rule_name,
        "mitre_technique": alert.mitre_technique,
        "severity": alert.severity,
        "triggered_at": alert.triggered_at,
        "matched_event_ids": alert.matched_events,
        "summary": alert.summary,
        "entity": alert.entity,
        "status": alert.status,
    }