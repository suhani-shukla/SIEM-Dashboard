"""
FILE LOCATION: backend/app/services/alerts.py

Alert service layer (Phase 4).

ASSUMPTIONS (adjust import paths to match your actual modules):
- app.models.alert.Alert          -> your existing Alert SQLAlchemy model
- app.models.alert_history.AlertHistory -> added this phase
- app.models.event.Event          -> your existing Event SQLAlchemy model
- app.db.session.get_db           -> async session dependency, yields AsyncSession
- app.core.redis.get_redis        -> returns an async redis client
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.alert_history import AlertHistory
from app.models.event import Event
from app.schemas.alert import VALID_TRANSITIONS, AlertStatusUpdate

ALERTS_UPDATED_CHANNEL = "alerts:updated"


class InvalidTransitionError(Exception):
    pass


async def list_alerts(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    mitre_technique: Optional[str] = None,
    entity: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Alert], int]:
    limit = max(1, min(limit, 500))

    stmt = select(Alert)
    count_stmt = select(func.count()).select_from(Alert)

    filters = []
    if status:
        filters.append(Alert.status == status)
    if severity:
        filters.append(Alert.severity == severity)
    if mitre_technique:
        filters.append(Alert.mitre_technique == mitre_technique)
    if entity:
        filters.append(Alert.entity == entity)
    if date_from:
        filters.append(Alert.triggered_at >= date_from)
    if date_to:
        filters.append(Alert.triggered_at <= date_to)

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    stmt = stmt.order_by(Alert.triggered_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    return list(alerts), total


async def get_alert_detail(db: AsyncSession, alert_id: uuid.UUID) -> Optional[dict]:
    alert = await db.get(Alert, alert_id)
    if alert is None:
        return None

    history_stmt = (
        select(AlertHistory)
        .where(AlertHistory.alert_id == alert_id)
        .order_by(AlertHistory.changed_at.asc())
    )
    history_result = await db.execute(history_stmt)
    history = history_result.scalars().all()

    matched_events: list[dict] = []
    if alert.matched_event_ids:
        events_stmt = select(Event).where(Event.id.in_(alert.matched_event_ids))
        events_result = await db.execute(events_stmt)
        matched_events = [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat(),
                "source": e.source,
                "event_type": e.event_type,
                "severity": e.severity,
                "raw_payload": e.raw_payload,
            }
            for e in events_result.scalars().all()
        ]

    return {"alert": alert, "history": history, "matched_events": matched_events}


async def update_alert_status(
    db: AsyncSession,
    redis_client,
    alert_id: uuid.UUID,
    update: AlertStatusUpdate,
) -> Alert:
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Alert not found"}})

    current_status = alert.status
    allowed = VALID_TRANSITIONS.get(current_status, set())

    if update.status == current_status:
        # No-op transition — allow it (e.g. re-submitting a note) without
        # writing a history row for a status change, but do record the note
        # if provided by treating it as a same-state annotation.
        pass
    elif update.status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition alert from '{current_status}' to '{update.status}'. "
            f"Valid next states: {sorted(allowed) or 'none (terminal state)'}"
        )

    history_row = AlertHistory(
        id=uuid.uuid4(),
        alert_id=alert.id,
        from_status=current_status,
        to_status=update.status,
        changed_by=update.changed_by,
        note=update.note,
        changed_at=datetime.now(timezone.utc),
    )
    db.add(history_row)

    alert.status = update.status
    alert.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(alert)

    # Best-effort live update push — don't fail the request if redis hiccups.
    try:
        await redis_client.publish(
            ALERTS_UPDATED_CHANNEL,
            json.dumps(
                {
                    "id": str(alert.id),
                    "status": alert.status,
                    "changed_by": update.changed_by,
                    "note": update.note,
                }
            ),
        )
    except Exception:
        pass

    return alert