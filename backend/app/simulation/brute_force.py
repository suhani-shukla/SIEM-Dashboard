"""
FILE LOCATION: backend/app/simulation/brute_force.py

Generates a brute force attack: repeated auth_failure events from one
source_ip against one target user, spaced with realistic jitter, optionally
followed by a successful login (simulating a successful compromise).

Maps to playbooks/brute_force.yaml (MITRE T1110), a ThresholdRule matching
event_type=auth_failure grouped by source_ip.
"""
from datetime import datetime
from typing import Optional

from app.simulation.base import (
    build_event,
    get_rng,
    jittered_delay,
    advance_time,
    random_internal_ip,
    random_external_ip,
    random_user,
)

_SERVICES = ["ssh", "vpn", "webapp-login", "rdp"]


def generate(
    start_time: datetime,
    seed: Optional[int] = None,
    compromise_probability: float = 0.4,
    force_success: Optional[bool] = None,
) -> list[dict]:
    """
    Returns a time-ordered list of event dicts.

    compromise_probability: chance the attack ends in an auth_success event.
    force_success: overrides the random roll if explicitly set (True/False).
    """
    rng = get_rng(seed)

    source_ip = random_external_ip(rng)
    target_user = random_user(rng)
    service = rng.choice(_SERVICES)

    attempt_count = rng.randint(6, 15)
    events: list[dict] = []
    current_time = start_time

    for attempt in range(1, attempt_count + 1):
        events.append(
            build_event(
                timestamp=current_time,
                source=service,
                event_type="auth_failure",
                severity="medium",
                raw_payload={
                    "source_ip": source_ip,
                    "user": target_user,
                    "service": service,
                    "attempt_number": attempt,
                    "reason": rng.choice(["invalid_password", "invalid_password", "account_locked_retry"]),
                },
            )
        )
        current_time = advance_time(current_time, jittered_delay(rng, 1.0, 10.0))

    should_succeed = force_success if force_success is not None else (rng.random() < compromise_probability)
    if should_succeed:
        events.append(
            build_event(
                timestamp=current_time,
                source=service,
                event_type="auth_success",
                severity="high",  # success after a failure burst is notable
                raw_payload={
                    "source_ip": source_ip,
                    "user": target_user,
                    "service": service,
                    "attempt_number": attempt_count + 1,
                },
            )
        )

    return events