from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import get_db
from app.schemas.event import EventCreate, EventResponse
from app.services.events import create_events

router = APIRouter(prefix="/events", tags=["events"])


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
