<!-- FILE LOCATION: project root, e.g. ./PHASE6_WIRING.md -->
# Phase 6 — Wiring Instructions

## 1. File placement

All frontend files go under `frontend/` at the paths in their own header
comments. This phase **replaces** your existing skeleton `App.jsx`,
`main.jsx`, `index.css`, `package.json`, `vite.config.js`,
`tailwind.config.js`, and `postcss.config.js` from Phase 1 — back those up
if you customized any of them, otherwise just overwrite.

New directories created this phase:
```
frontend/src/api/
frontend/src/hooks/
frontend/src/components/layout/
frontend/src/components/common/
frontend/src/pages/
```

`docker-compose.yml`, `docker-compose.prod.yml`, and `PHASE6_WIRING.md` go
at the project root. `docker-compose.yml` here is a full replacement
reflecting the real Phase 1-5 architecture (api, postgres, redis,
frontend) — merge in any custom environment variables you'd already added.

## 2. Install dependencies

```bash
docker compose build frontend
```
(The `npm install` happens inside the Dockerfile build stage — no need to
run npm locally unless you want IDE autocomplete, in which case also run
`cd frontend && npm install` on your host.)

## 3. Backend CORS check

Your FastAPI `api` service needs to allow requests from the frontend
origin. In dev mode the Vite proxy avoids CORS entirely (browser only ever
talks to `localhost:5173`, which proxies server-side to `api:8000`), so
**you likely need no CORS changes for dev**. In prod mode, nginx proxies
`/api` same-origin too, so CORS isn't needed there either. You only need
`CORSMiddleware` in FastAPI if you ever call the API directly from a
different origin (e.g. testing the API standalone from a browser).

## 4. justfile additions

```just
frontend-install:
    docker compose exec frontend npm install

demo:
    just up
    just migrate
    just simulate-all
    @echo ""
    @echo "✅ Demo ready — open http://localhost:5173 (dev) or http://localhost (prod build)"
```

## 5. Rebuild and bring everything up

```bash
just down
just up
```

Check the frontend container specifically:
```bash
docker compose logs frontend --tail=50
```
You should see Vite's dev server startup message and no proxy errors.

## 6. Production build check (optional but recommended before calling Phase 6 done)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
Open http://localhost (port 80, not 5173) and confirm the built SPA loads
and the live SSE feed still connects — nginx's `proxy_buffering off` in
`nginx.conf` is what makes SSE actually work in this mode; if you ever see
the live feed hang in prod but work fine in dev, that config is the first
place to check.

## Notes / assumptions to reconcile against your real backend

- API paths are assumed to be mounted under `/api/v1/...` (e.g.
  `/api/v1/alerts`, `/api/v1/events`, `/api/v1/playbooks`,
  `/api/v1/simulate`). If your FastAPI app mounts the v1 router directly at
  `/v1/...` without an `/api` prefix, either add the prefix in your main
  app, or change `BASE_URL` in `frontend/src/api/client.js` and the nginx
  `location` block accordingly.
- `Alert.mitre_technique` and `Playbook.mitre_attack.{technique_id,
  technique_name, tactic}` field names are assumed per earlier phases —
  double check these match your actual Pydantic schema field names.
- The tactic labels in `Playbooks.jsx`'s `TACTICS` array ("Credential
  Access", "Exfiltration", "Initial Access", "Privilege Escalation") are
  assumed to match your playbook YAMLs' `mitre_attack.tactic` values
  exactly (case-insensitive, spaces become hyphens for matching). Adjust
  if your YAML tactic strings differ.
