<!-- FILE LOCATION: README.md (project root) -->
# SIEM Dashboard

A self-contained Security Information and Event Management console: real-time
log ingestion, rule-based correlation across three evaluator types, four
MITRE ATT&CK-mapped attack playbooks, live alert streaming, full alert
lifecycle management, and a built-in attack simulator for demos and
integration testing.

## Architecture

```
                     ┌─────────────┐
   attack sim  ─────▶│             │
   (Phase 5)         │   FastAPI   │──── SSE ────▶  React dashboard
                      │     api     │                (Phase 6)
   log sources ──────▶│             │◀──── REST ─────
                      └──────┬──────┘
                             │
                 ┌───────────┼────────────┐
                 ▼                        ▼
           ┌──────────┐             ┌──────────┐
           │ Postgres │             │  Redis   │
           │ (events, │             │ (sliding │
           │  alerts) │             │ windows, │
           └──────────┘             │ pub/sub) │
                                     └────┬─────┘
                                          │
                              rule engine (Threshold /
                              Sequence / Aggregation),
                              running as a background
                              task inside the api process,
                              driven by playbooks/*.yaml
```

- **Ingestion**: events POSTed to `/api/v1/events` land in Postgres and are
  published to Redis for correlation.
- **Correlation engine**: a background task inside the `api` process
  subscribes to that Redis channel and evaluates every event against all
  enabled playbooks (Threshold / Sequence / Aggregation rule types).
- **Playbooks**: YAML files in `/playbooks`, each mapped to a MITRE ATT&CK
  technique, loaded at startup.
- **Alerts**: fired alerts go to Postgres with a full lifecycle
  (new → acknowledged → investigating → resolved/false_positive) and an
  audit trail, and are pushed live over SSE.
- **Simulation engine**: generates realistic multi-stage attack traffic for
  all four playbooks, usable via CLI, justfile, or the dashboard's
  "Run Simulation" buttons.
- **Frontend**: React SPA — dashboard overview, alerts table + detail, log
  viewer, and a MITRE coverage matrix.

## Stack

Python 3.11 / FastAPI · PostgreSQL 15 · Redis 7 · React 18 + Vite +
Tailwind · Docker Compose · Just

## Setup

```bash
just up          # bring up postgres, redis, api, frontend (dev mode)
just migrate      # run database migrations
just seed         # optional: seed some baseline sample events
```

Open the dashboard at **http://localhost:5173**.

## Quick demo

The fastest way to see everything working:

```bash
just demo
```

This brings the stack up, runs migrations, fires all four attack
simulations, and prints the dashboard URL. Then:

1. Open http://localhost:5173/dashboard — you'll see summary cards
   populate, the event volume chart fill in, and the live feed panel show
   the alerts that just fired.
2. Go to **Alerts** — filter by severity or MITRE technique, click into
   one, and walk it through its lifecycle (acknowledge → investigate →
   resolve), watching the audit trail build.
3. From an alert's detail page, click **"View surrounding log activity"**
   to jump to the **Log Viewer** pre-filtered around that alert's time
   window and entity.
4. Go to **Playbooks** — see the MITRE coverage grid light up for all four
   covered tactics, and try toggling a playbook off/on.
5. Back on the dashboard, click any **Run Simulation** button to trigger a
   fresh attack live and watch it land in the feed within a couple seconds.

## Production deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

This serves the frontend as a static build behind nginx (port 80) instead
of the Vite dev server, with nginx reverse-proxying `/api` to the backend
(SSE-safe — buffering is disabled for that path).

## Project layout

```
/backend      FastAPI app: ingestion, rule engine, playbooks, alerts, simulation
/frontend     React dashboard
/playbooks    YAML attack playbooks mapped to MITRE ATT&CK
docker-compose.yml         dev configuration
docker-compose.prod.yml    production overlay
justfile                   task automation
```

## Common commands

| Command | What it does |
|---|---|
| `just up` / `just down` | Start / stop the stack |
| `just migrate` | Run Alembic migrations |
| `just seed` | Seed sample log events |
| `just simulate brute_force` | Run one attack simulation (fast mode) |
| `just simulate-all` | Run all four attack simulations |
| `just test-e2e` | Full pipeline integration test |
| `just demo` | Up + migrate + simulate-all in one shot |
