I'm building a SIEM (Security Information and Event Management) dashboard. Full spec:

STACK:
- Backend: Python 3.11+, FastAPI, async/await throughout
- Database: PostgreSQL 15 (structured storage), Redis 7 (sliding windows, pub/sub, correlation state)
- Frontend: React 18 + Vite + Tailwind CSS, recharts for charts
- Task automation: Just (justfile) — NOT Make
- Deployment: Docker Compose (services: api, worker, postgres, redis, frontend, nginx)
- Package management: Python via `uv` or `pip` with requirements.txt/pyproject.toml, Node via npm

CORE FEATURES:
1. Real-time log ingestion + event correlation engine with 3 rule types: Threshold, Sequence, Aggregation
2. Four YAML-based attack playbooks mapped to MITRE ATT&CK: brute force, DNS tunneling, phishing, privilege escalation
3. Server-Sent Events (SSE) for live alert feed
4. Paginated, filterable log viewer (filter by time range, severity, source, event_type)
5. Alert lifecycle: new -> acknowledged -> investigating -> resolved / false_positive, with audit trail
6. Attack simulation engine generating realistic multi-stage event sequences for testing/demo
7. Full Docker Compose deployment, orchestrated via a justfile

CONVENTIONS:
- All timestamps UTC, ISO 8601
- All API responses JSON, errors follow {"error": {"code": str, "message": str}}
- Rule evaluators implement a common interface: evaluate(event, context) -> Alert | None
- Playbooks are YAML files loaded at startup from a /playbooks directory
- Keep code in a monorepo: /backend, /frontend, /playbooks, /justfile, /docker-compose.yml

Acknowledge you understand this context. I will now give you phase-by-phase instructions — implement only what's asked in each phase, but keep the above architecture in mind so later phases integrate cleanly.