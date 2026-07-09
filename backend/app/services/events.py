import json

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import EVENTS_RAW_CHANNEL
from app.models.event import Event
from app.schemas.event import EventCreate, EventResponse


def _event_to_model(data: EventCreate) -> Event:
    return Event(
        timestamp=data.timestamp,
        source=data.source,
        event_type=data.event_type,
        severity=data.severity.value,
        raw_payload=data.raw_payload,
        event_metadata=data.metadata,
    )


async def create_events(
    db: AsyncSession,
    redis_client: Redis,
    events_in: list[EventCreate],
) -> list[Event]:
    events = [_event_to_model(e) for e in events_in]
    db.add_all(events)
    await db.commit()
    for event in events:
        await db.refresh(event)

    for event in events:
        payload = EventResponse.from_orm_event(event).model_dump(mode="json")
        await redis_client.publish(EVENTS_RAW_CHANNEL, json.dumps(payload))

    return events
