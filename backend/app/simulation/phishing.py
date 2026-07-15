"""
FILE LOCATION: backend/app/simulation/phishing.py

Generates a phishing attack: a 3-stage sequence for one user —
email_received (suspicious link) -> link_clicked -> credential_submitted
(on an external domain).

Maps to playbooks/phishing.yaml (MITRE T1566), a SequenceRule with those
three steps in order, grouped by user, within a window (default 600s per
the Phase 3 playbook).
"""
import uuid
from datetime import datetime
from typing import Optional

from app.simulation.base import (
    build_event,
    get_rng,
    jittered_delay,
    advance_time,
    random_user,
)

_FAKE_SENDER_DOMAINS = [
    "secure-mail-verify.com",
    "account-update-portal.net",
    "hr-benefits-notice.org",
    "it-support-helpdesk.info",
]

_LURE_SUBJECTS = [
    "Action Required: Verify Your Account",
    "Your Password Will Expire Today",
    "HR: Updated Benefits Enrollment Deadline",
    "IT Alert: Suspicious Sign-in Detected",
]


def generate(start_time: datetime, seed: Optional[int] = None) -> list[dict]:
    rng = get_rng(seed)

    target_user = random_user(rng)
    sender_domain = rng.choice(_FAKE_SENDER_DOMAINS)
    subject = rng.choice(_LURE_SUBJECTS)
    phishing_url = f"https://{sender_domain}/verify?token={uuid.uuid4().hex[:12]}"

    email_time = start_time
    click_time = advance_time(email_time, jittered_delay(rng, 30, 300))
    submit_time = advance_time(click_time, jittered_delay(rng, 10, 60))

    events = [
        build_event(
            timestamp=email_time,
            source="mail-gateway",
            event_type="email_received",
            severity="medium",
            raw_payload={
                "user": target_user,
                "sender_domain": sender_domain,
                "subject": subject,
                "suspicious_link": True,
                "link_url": phishing_url,
            },
        ),
        build_event(
            timestamp=click_time,
            source="proxy",
            event_type="link_clicked",
            severity="high",
            raw_payload={
                "user": target_user,
                "url": phishing_url,
                "referrer": "webmail-client",
            },
        ),
        build_event(
            timestamp=submit_time,
            source="proxy",
            event_type="credential_submitted",
            severity="critical",
            raw_payload={
                "user": target_user,
                "url": phishing_url,
                "external_domain": True,
                "form_fields": ["username", "password"],
            },
        ),
    ]
    return events