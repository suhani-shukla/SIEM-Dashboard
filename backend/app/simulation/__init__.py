"""
FILE LOCATION: backend/app/simulation/__init__.py
"""
from app.simulation import brute_force, dns_tunneling, phishing, privilege_escalation

GENERATORS = {
    "brute_force": brute_force.generate,
    "dns_tunneling": dns_tunneling.generate,
    "phishing": phishing.generate,
    "privilege_escalation": privilege_escalation.generate,
}

ATTACK_TYPES = list(GENERATORS.keys())