from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy import select, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import get_db
from app.models.event import Event
from app.schemas.event import EventCreate, EventResponse  # adjust name if yours differs
from app.services.events import create_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    severity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Free-text search over raw_payload"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Event)
    count_stmt = select(func.count()).select_from(Event)

    filters = []
    if date_from:
        filters.append(Event.timestamp >= date_from)
    if date_to:
        filters.append(Event.timestamp <= date_to)
    if severity:
        filters.append(Event.severity == severity)
    if source:
        filters.append(Event.source == source)
    if event_type:
        filters.append(Event.event_type == event_type)
    if q:
        # Simple text search by casting the jsonb payload to text.
        # Fine for moderate volumes; swap for a GIN-indexed tsvector column
        # or pg_trgm if this becomes a bottleneck at scale.
        filters.append(cast(Event.raw_payload, String).ilike(f"%{q}%"))

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    stmt = stmt.order_by(Event.timestamp.desc()).limit(limit + 1).offset(offset)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    return {
        "items": [EventResponse.from_orm_event(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }


@router.post(
    "",
    response_model=EventResponse | list[EventResponse],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_events(
    payload: EventCreate | list[EventCreate],
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> EventResponse | list[EventResponse]:
    events_in = payload if isinstance(payload, list) else [payload]
    events = await create_events(db, redis_client, events_in)
    if isinstance(payload, list):
        return [EventResponse.from_orm_event(e) for e in events]
    return EventResponse.from_orm_event(events[0])