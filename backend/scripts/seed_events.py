#!/usr/bin/env python3
"""Seed ~50 sample events via the ingestion API."""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone

import httpx

SOURCES = ["firewall", "auth-server", "dns-resolver", "endpoint-agent", "mail-gateway"]
EVENT_TYPES = [
    "login_failed",
    "login_success",
    "dns_query",
    "file_access",
    "process_start",
    "network_connection",
    "email_received",
    "privilege_change",
]
SEVERITIES = ["info", "low", "medium", "high", "critical"]

API_URL = "http://localhost:8000/api/v1/events"
EVENT_COUNT = 50


def build_events(count: int = EVENT_COUNT) -> list[dict]:
    now = datetime.now(timezone.utc)
    events = []
    for i in range(count):
        ts = now - timedelta(minutes=random.randint(0, 120))
        source = random.choice(SOURCES)
        event_type = random.choice(EVENT_TYPES)
        severity = random.choice(SEVERITIES)
        events.append(
            {
                "timestamp": ts.isoformat(),
                "source": source,
                "event_type": event_type,
                "severity": severity,
                "raw_payload": {
                    "message": f"Sample event #{i + 1}",
                    "host": f"host-{random.randint(1, 20)}",
                    "user": f"user{random.randint(1, 50)}",
                },
                "metadata": {
                    "seed": True,
                    "batch": "initial",
                },
            }
        )
    return events


def main() -> int:
    events = build_events()
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(API_URL, json=events)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Failed to seed events: {exc}", file=sys.stderr)
        return 1

    created = response.json()
    count = len(created) if isinstance(created, list) else 1
    print(f"Seeded {count} events via {API_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
