"""
FILE LOCATION: backend/app/schemas/alert.py

Pydantic schemas for the alerts API (Phase 4).

ASSUMPTION: severity is one of "info","low","medium","high","critical" and
status is one of "new","acknowledged","investigating","resolved","false_positive"
matching the Phase 2/3 spec. Adjust the Literal types below if your actual
values differ.
"""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

AlertStatus = Literal["new", "acknowledged", "investigating", "resolved", "false_positive"]
Severity = Literal["info", "low", "medium", "high", "critical"]

# Legal transitions — used by the service layer to validate PATCH requests.
# Reopening from a terminal state back into investigation is allowed;
# jumping straight from "new" to "resolved" is not (must acknowledge first).
VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"acknowledged", "false_positive"},
    "acknowledged": {"investigating", "false_positive", "resolved"},
    "investigating": {"resolved", "false_positive", "acknowledged"},
    "resolved": {"investigating"},
    "false_positive": {"investigating"},
}


class AlertHistoryEntry(BaseModel):
    id: UUID
    from_status: str
    to_status: str
    changed_by: str
    note: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: UUID
    rule_name: str
    mitre_technique: Optional[str] = None
    severity: Severity
    triggered_at: datetime
    matched_event_ids: list[UUID] = Field(default_factory=list)
    summary: Optional[str] = None
    entity: Optional[str] = None
    status: AlertStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertDetailResponse(AlertResponse):
    history: list[AlertHistoryEntry] = Field(default_factory=list)
    matched_events: list[dict] = Field(default_factory=list)  # full raw events, joined in


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    limit: int
    offset: int


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    changed_by: str = Field(..., min_length=1, max_length=128)
    note: Optional[str] = Field(None, max_length=2000)