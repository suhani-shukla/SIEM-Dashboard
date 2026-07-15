"""
FILE LOCATION: backend/app/simulation/base.py

Shared helpers used by every attack generator: building EventCreate-shaped
dicts, realistic jittered timing, random identifiers, and benign background
noise events (interleaved with attack traffic so detection isn't trivial).
"""
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

# --- identifiers -----------------------------------------------------------

_USERS = [
    "jsmith", "agarcia", "mchen", "rpatel", "kwilliams",
    "tnguyen", "dkim", "lmartin", "sbrown", "eovalle",
]

_BENIGN_EVENT_TYPES = [
    "health_check", "page_view", "file_access", "api_call",
    "logout", "session_refresh", "config_read",
]

_BENIGN_SOURCES = ["web-app", "internal-api", "vpn-gateway", "file-server", "auth-service"]


def random_user(rng: random.Random) -> str:
    return rng.choice(_USERS)


def random_internal_ip(rng: random.Random) -> str:
    return f"10.0.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def random_external_ip(rng: random.Random) -> str:
    # Avoid real allocated ranges by staying in documentation/test-safe-ish blocks
    return f"{rng.randint(1, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def random_high_entropy_label(rng: random.Random, length: Optional[int] = None) -> str:
    """Random base32/hex-looking string, mimicking DNS tunneling subdomain labels."""
    length = length or rng.randint(20, 40)
    alphabet = string.ascii_lowercase + string.digits
    return "".join(rng.choice(alphabet) for _ in range(length))


# --- event construction ------------------------------------------------------

def build_event(
    timestamp: datetime,
    source: str,
    event_type: str,
    severity: str,
    raw_payload: dict,
) -> dict:
    """
    Builds a dict matching the Phase 1 EventCreate schema. Timestamps are
    serialized to ISO 8601 UTC, matching the project convention.
    """
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return {
        "timestamp": timestamp.astimezone(timezone.utc).isoformat(),
        "source": source,
        "event_type": event_type,
        "severity": severity,
        "raw_payload": raw_payload,
    }


# --- timing helpers ----------------------------------------------------------

def jittered_delay(rng: random.Random, low: float, high: float) -> float:
    """Uniform delay with a touch of gaussian jitter so timing doesn't look robotic."""
    base = rng.uniform(low, high)
    jitter = rng.gauss(0, (high - low) * 0.1)
    return max(0.05, base + jitter)


def advance_time(current: datetime, seconds: float) -> datetime:
    return current + timedelta(seconds=seconds)


# --- background noise ---------------------------------------------------------

def generate_noise_events(
    rng: random.Random,
    count: int,
    start_time: datetime,
    end_time: datetime,
) -> list[dict]:
    """
    Generates unrelated benign events scattered randomly across
    [start_time, end_time], so attack traffic isn't the only thing in the
    ingestion stream during a simulation run.
    """
    if count <= 0 or end_time <= start_time:
        return []

    span_seconds = (end_time - start_time).total_seconds()
    events = []
    for _ in range(count):
        offset = rng.uniform(0, span_seconds)
        ts = advance_time(start_time, offset)
        event_type = rng.choice(_BENIGN_EVENT_TYPES)
        source = rng.choice(_BENIGN_SOURCES)
        user = random_user(rng)
        events.append(
            build_event(
                timestamp=ts,
                source=source,
                event_type=event_type,
                severity="info",
                raw_payload={
                    "user": user,
                    "source_ip": random_internal_ip(rng),
                    "request_id": str(uuid.uuid4()),
                },
            )
        )
    return events


def get_rng(seed: Optional[int]) -> random.Random:
    return random.Random(seed) if seed is not None else random.Random()