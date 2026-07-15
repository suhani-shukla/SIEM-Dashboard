"""
FILE LOCATION: backend/app/api/v1/simulate.py

Wire this up in app/api/v1/router.py:

    from app.api.v1 import simulate

    router.include_router(simulate.router, prefix="/simulate", tags=["simulation"])

POST /api/v1/simulate       -> kicks off a simulation as a background task, returns immediately
GET  /api/v1/simulate/{id}/status -> poll for progress/completion

Status is tracked in a Redis hash (sim:{id}) rather than in-memory, so it
survives across multiple worker processes/replicas.
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.redis import get_redis
from app.schemas.simulation import (
    SimulationRequest,
    SimulationStatusResponse,
    SimulationTriggerResponse,
)
from app.simulation.runner import run_simulation

router = APIRouter()

SIM_KEY_PREFIX = "sim:"
SIM_TTL_SECONDS = 60 * 60 * 24  # keep status around for a day


def _sim_key(simulation_id: str) -> str:
    return f"{SIM_KEY_PREFIX}{simulation_id}"


async def _run_and_track(simulation_id: str, request: SimulationRequest, redis_client):
    key = _sim_key(simulation_id)
    try:
        summary = await run_simulation(
            attack_type=request.attack_type,
            mode=request.mode,
            noise_events=request.noise_events,
            seed=request.seed,
        )
        await redis_client.hset(
            key,
            mapping={
                "status": "completed",
                "events_sent": str(summary["events_sent"]),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        await redis_client.hset(
            key,
            mapping={
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    await redis_client.expire(key, SIM_TTL_SECONDS)


@router.post("", response_model=SimulationTriggerResponse, status_code=202)
async def trigger_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    redis_client=Depends(get_redis),
):
    simulation_id = str(uuid.uuid4())
    key = _sim_key(simulation_id)
    started_at = datetime.now(timezone.utc).isoformat()

    await redis_client.hset(
        key,
        mapping={
            "status": "running",
            "attack_type": request.attack_type,
            "mode": request.mode,
            "started_at": started_at,
        },
    )
    await redis_client.expire(key, SIM_TTL_SECONDS)

    background_tasks.add_task(_run_and_track, simulation_id, request, redis_client)

    return SimulationTriggerResponse(
        simulation_id=simulation_id,
        attack_type=request.attack_type,
        mode=request.mode,
        status="running",
    )


@router.get("/{simulation_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(simulation_id: str, redis_client=Depends(get_redis)):
    key = _sim_key(simulation_id)
    data = await redis_client.hgetall(key)
    if not data:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "Simulation not found or expired"}},
        )

    # redis-py returns bytes unless decode_responses=True is set on the client;
    # normalize either way.
    decoded = {
        (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
        for k, v in data.items()
    }

    return SimulationStatusResponse(
        simulation_id=simulation_id,
        attack_type=decoded.get("attack_type", "unknown"),
        mode=decoded.get("mode", "unknown"),
        status=decoded.get("status", "running"),
        events_sent=int(decoded["events_sent"]) if "events_sent" in decoded else None,
        started_at=decoded["started_at"],
        completed_at=decoded.get("completed_at"),
        error=decoded.get("error"),
    )