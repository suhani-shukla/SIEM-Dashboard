import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.event import Severity


class EventCreate(BaseModel):
    timestamp: datetime
    source: str
    event_type: str
    severity: Severity
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timestamp: datetime
    source: str
    event_type: str
    severity: Severity
    raw_payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime

    @field_serializer("timestamp", "ingested_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()

    @classmethod
    def from_orm_event(cls, event: Any) -> "EventResponse":
        return cls(
            id=event.id,
            timestamp=event.timestamp,
            source=event.source,
            event_type=event.event_type,
            severity=event.severity,
            raw_payload=event.raw_payload,
            metadata=event.event_metadata,
            ingested_at=event.ingested_at,
        )
