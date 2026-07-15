"""
FILE LOCATION: backend/app/simulation/runner.py

Orchestrates a named simulation: generates the attack event sequence (plus
interleaved benign noise), sorts everything by timestamp, and sends it to
the Phase 1 ingestion endpoint — either in "realtime" mode (actually
sleeping between sends to mimic live traffic) or "fast" mode (single batch
POST, timestamps preserved but no wall-clock delay).

Design note: `http_client` is injectable so tests can pass an
httpx.AsyncClient bound to the FastAPI app in-process (via ASGITransport)
instead of hitting a real running server over the network. See
tests/test_e2e.py for the pattern.
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.simulation import GENERATORS, ATTACK_TYPES
from app.simulation.base import generate_noise_events, get_rng

DEFAULT_API_BASE_URL = os.environ.get("SIMULATION_API_BASE_URL", "http://localhost:8000")
INGEST_PATH = "/api/v1/events"


class UnknownAttackTypeError(ValueError):
    pass


def _build_event_list(
    attack_type: str,
    start_time: datetime,
    seed: Optional[int],
    noise_events: int,
) -> list[dict]:
    if attack_type not in GENERATORS:
        raise UnknownAttackTypeError(
            f"Unknown attack_type '{attack_type}'. Valid options: {ATTACK_TYPES}"
        )

    generator = GENERATORS[attack_type]
    attack_events = generator(start_time=start_time, seed=seed)

    if not attack_events:
        return attack_events

    # Noise spans from just before the attack starts to just after it ends,
    # so background traffic isn't obviously bracketed around the attack.
    first_ts = datetime.fromisoformat(attack_events[0]["timestamp"])
    last_ts = datetime.fromisoformat(attack_events[-1]["timestamp"])

    rng = get_rng(seed)
    noise_start = first_ts.replace(tzinfo=timezone.utc) if first_ts.tzinfo is None else first_ts
    noise_end = last_ts.replace(tzinfo=timezone.utc) if last_ts.tzinfo is None else last_ts
    from datetime import timedelta
    noise = generate_noise_events(
        rng,
        count=noise_events,
        start_time=noise_start - timedelta(seconds=30),
        end_time=noise_end + timedelta(seconds=30),
    )

    combined = attack_events + noise
    combined.sort(key=lambda e: e["timestamp"])
    return combined


async def _send_fast(client: httpx.AsyncClient, events: list[dict]) -> int:
    """Single batch POST — timestamps are preserved as generated, no sleeping."""
    if not events:
        return 0
    resp = await client.post(INGEST_PATH, json=events)
    resp.raise_for_status()
    return len(events)


async def _send_realtime(client: httpx.AsyncClient, events: list[dict]) -> int:
    """Sends events one at a time, sleeping the real delta between timestamps."""
    if not events:
        return 0

    sent = 0
    prev_ts: Optional[datetime] = None
    for event in events:
        ts = datetime.fromisoformat(event["timestamp"])
        if prev_ts is not None:
            delta = (ts - prev_ts).total_seconds()
            if delta > 0:
                await asyncio.sleep(min(delta, 30))  # cap absurd gaps for demo purposes
        resp = await client.post(INGEST_PATH, json=event)
        resp.raise_for_status()
        sent += 1
        prev_ts = ts

    return sent


async def run_simulation(
    attack_type: str,
    mode: str = "fast",
    noise_events: int = 20,
    seed: Optional[int] = None,
    http_client: Optional[httpx.AsyncClient] = None,
    api_base_url: Optional[str] = None,
    start_time: Optional[datetime] = None,
) -> dict:
    """
    Runs one simulation (or "all" of them sequentially). Returns a summary
    dict: {attack_type, mode, events_sent, attacks_run: [...]}.
    """
    if mode not in ("fast", "realtime"):
        raise ValueError(f"mode must be 'fast' or 'realtime', got '{mode}'")

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(
        base_url=api_base_url or DEFAULT_API_BASE_URL, timeout=30.0
    )

    try:
        if attack_type == "all":
            results = []
            total_sent = 0
            for i, name in enumerate(ATTACK_TYPES):
                # stagger each attack's start slightly so "all" doesn't produce
                # every attack starting at the exact same instant
                attack_start = start_time or datetime.now(timezone.utc)
                per_attack_seed = None if seed is None else seed + i
                summary = await run_simulation(
                    attack_type=name,
                    mode=mode,
                    noise_events=noise_events,
                    seed=per_attack_seed,
                    http_client=client,
                    start_time=attack_start,
                )
                results.append(summary)
                total_sent += summary["events_sent"]
                if mode == "realtime":
                    await asyncio.sleep(2)  # brief gap between attacks

            return {
                "attack_type": "all",
                "mode": mode,
                "events_sent": total_sent,
                "attacks_run": results,
            }

        start_time = start_time or datetime.now(timezone.utc)
        events = _build_event_list(attack_type, start_time, seed, noise_events)

        if mode == "fast":
            sent = await _send_fast(client, events)
        else:
            sent = await _send_realtime(client, events)

        return {
            "attack_type": attack_type,
            "mode": mode,
            "events_sent": sent,
            "noise_events_requested": noise_events,
        }
    finally:
        if owns_client:
            await client.aclose()