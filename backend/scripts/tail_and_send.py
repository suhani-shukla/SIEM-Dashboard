#!/usr/bin/env python3
"""Read newline-delimited JSON events from a file or stdin and POST to the ingestion API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send NDJSON events to the SIEM ingestion API")
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Path to NDJSON file, or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/v1/events",
        help="Ingestion endpoint URL",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Send all events in a single batch request",
    )
    return parser.parse_args()


def iter_events(source: str) -> list[dict]:
    if source == "-":
        lines = sys.stdin
    else:
        lines = Path(source).read_text(encoding="utf-8").splitlines()

    events = []
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"Skipping invalid JSON on line {line_num}: {exc}", file=sys.stderr)
    return events


def main() -> int:
    args = parse_args()
    events = iter_events(args.input)
    if not events:
        print("No events to send.", file=sys.stderr)
        return 1

    with httpx.Client(timeout=30.0) as client:
        if args.batch:
            response = client.post(args.url, json=events)
            response.raise_for_status()
            created = response.json()
            count = len(created) if isinstance(created, list) else 1
        else:
            count = 0
            for event in events:
                response = client.post(args.url, json=event)
                response.raise_for_status()
                count += 1

    print(f"Successfully sent {count} event(s) to {args.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
