"""
FILE LOCATION: backend/app/simulation/dns_tunneling.py

Generates a DNS tunneling / exfiltration-over-DNS attack: many dns_query
events from one source_ip, querying high-entropy subdomains of a single
base domain, sent in tight bursts (mimicking beaconing behavior).

Maps to playbooks/dns_tunneling.yaml (MITRE T1071.004), an AggregationRule
matching event_type=dns_query, grouped by source_ip, counting distinct
queried subdomains within the window.
"""
from datetime import datetime
from typing import Optional

from app.simulation.base import (
    build_event,
    get_rng,
    jittered_delay,
    advance_time,
    random_internal_ip,
    random_high_entropy_label,
)

_SUSPICIOUS_BASE_DOMAINS = [
    "cdn-assets-sync.net",
    "telemetry-relay.info",
    "static-content-cache.biz",
    "update-service-mirror.top",
]


def generate(
    start_time: datetime,
    seed: Optional[int] = None,
    query_count: Optional[int] = None,
) -> list[dict]:
    rng = get_rng(seed)

    source_ip = random_internal_ip(rng)  # exfil source is typically an internal host
    base_domain = rng.choice(_SUSPICIOUS_BASE_DOMAINS)
    total_queries = query_count or rng.randint(30, 60)

    events: list[dict] = []
    current_time = start_time
    remaining = total_queries

    # Send in tight bursts (5-10 queries) separated by short pauses, rather
    # than one perfectly uniform stream — closer to real beaconing behavior.
    while remaining > 0:
        burst_size = min(remaining, rng.randint(5, 10))
        for _ in range(burst_size):
            subdomain = random_high_entropy_label(rng)
            qname = f"{subdomain}.{base_domain}"
            events.append(
                build_event(
                    timestamp=current_time,
                    source="dns-resolver",
                    event_type="dns_query",
                    severity="low",  # individually low severity; the aggregation is what matters
                    raw_payload={
                        "source_ip": source_ip,
                        "query": qname,
                        "base_domain": base_domain,
                        "subdomain_label": subdomain,
                        "query_type": rng.choice(["TXT", "A", "CNAME"]),
                        "label_length": len(subdomain),
                    },
                )
            )
            current_time = advance_time(current_time, jittered_delay(rng, 0.1, 1.0))

        remaining -= burst_size
        if remaining > 0:
            # pause between bursts
            current_time = advance_time(current_time, jittered_delay(rng, 3.0, 12.0))

    return events