"""
FILE LOCATION: backend/app/api/v1/alerts.py

Phase 4: Alert lifecycle endpoints + SSE live feed.

Wire this up by adding to your app/api/v1/router.py:

    from app.api.v1 import alerts
    router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])

ASSUMPTION: app.core.redis exposes `get_redis()` as a FastAPI dependency
that yields an async redis client (matching your Phase 1/2 setup where the
rule engine publishes fired alerts to the "alerts:new" channel).
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import get_db
from app.schemas.alert import (
    AlertDetailResponse,
    AlertHistoryEntry,
    AlertListResponse,
    AlertResponse,
    AlertStatusUpdate,
)
from app.services import alerts as alert_service

router = APIRouter()

NEW_ALERTS_CHANNEL = "alerts:new"
KEEPALIVE_SECONDS = 15


@router.get("", response_model=AlertListResponse)
async def get_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    mitre_technique: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    alerts, total = await alert_service.list_alerts(
        db,
        status=status,
        severity=severity,
        mitre_technique=mitre_technique,
        entity=entity,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stream")
async def stream_alerts(request: Request, redis_client=Depends(get_redis)):
    """
    Server-Sent Events endpoint. Connect with an EventSource client:

        const es = new EventSource("/api/v1/alerts/stream");
        es.addEventListener("new_alert", (e) => { ... JSON.parse(e.data) ... });

    Emits `: keepalive` comments periodically to survive idle proxy timeouts.
    """

    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(NEW_ALERTS_CHANNEL)
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=KEEPALIVE_SECONDS,
                    )
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if message is None:
                    continue

                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                yield f"event: new_alert\ndata: {data}\n\n"
        finally:
            await pubsub.unsubscribe(NEW_ALERTS_CHANNEL)
            await pubsub.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering for SSE
        },
    )


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(alert_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    detail = await alert_service.get_alert_detail(db, alert_id)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "Alert not found"}},
        )

    alert = detail["alert"]
    response = AlertDetailResponse.model_validate(alert)
    response.history = [
        AlertHistoryEntry.model_validate(h)
        for h in detail["history"]
    ]
    response.matched_events = detail["matched_events"]
    return response


@router.patch("/{alert_id}/status", response_model=AlertResponse)
async def patch_alert_status(
    alert_id: uuid.UUID,
    update: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
):
    try:
        alert = await alert_service.update_alert_status(db, redis_client, alert_id, update)
    except alert_service.InvalidTransitionError as e:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "invalid_transition", "message": str(e)}},
        )
    return AlertResponse.model_validate(alert)