"""
FILE LOCATION: backend/app/simulation/privilege_escalation.py

Generates a privilege escalation attack: login_success, then 1-3
permission_denied probing attempts, then a privilege_change to admin —
for one user, spread over a few minutes.

Maps to playbooks/privilege_escalation.yaml (MITRE T1078/T1068), a
SequenceRule with those three steps in order, grouped by user, within a
300s window per the Phase 3 playbook.
"""
from datetime import datetime
from typing import Optional

from app.simulation.base import (
    build_event,
    get_rng,
    jittered_delay,
    advance_time,
    random_internal_ip,
    random_user,
)

_RESTRICTED_RESOURCES = [
    "/admin/users",
    "/admin/audit-logs",
    "/system/config",
    "/billing/export",
    "/admin/roles",
]


def generate(start_time: datetime, seed: Optional[int] = None) -> list[dict]:
    rng = get_rng(seed)

    target_user = random_user(rng)
    source_ip = random_internal_ip(rng)

    events: list[dict] = []
    current_time = start_time

    events.append(
        build_event(
            timestamp=current_time,
            source="auth-service",
            event_type="login_success",
            severity="info",
            raw_payload={
                "user": target_user,
                "source_ip": source_ip,
            },
        )
    )
    current_time = advance_time(current_time, jittered_delay(rng, 20, 90))

    probe_count = rng.randint(1, 3)
    for _ in range(probe_count):
        resource = rng.choice(_RESTRICTED_RESOURCES)
        events.append(
            build_event(
                timestamp=current_time,
                source="app-server",
                event_type="permission_denied",
                severity="medium",
                raw_payload={
                    "user": target_user,
                    "source_ip": source_ip,
                    "resource": resource,
                    "required_role": "admin",
                },
            )
        )
        current_time = advance_time(current_time, jittered_delay(rng, 15, 60))

    # gap before the actual escalation, still within the ~5 minute window
    current_time = advance_time(current_time, jittered_delay(rng, 30, 90))

    events.append(
        build_event(
            timestamp=current_time,
            source="admin-console",
            event_type="privilege_change",
            severity="critical",
            raw_payload={
                "user": target_user,
                "source_ip": source_ip,
                "new_privilege": "admin",
                "changed_by": target_user,  # self-escalation, the suspicious part
            },
        )
    )

    return events