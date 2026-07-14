# SIEM Dashboard â€” development commands

set dotenv-load

up:
    docker compose up -d --build

down:
    docker compose down

migrate:
    docker compose exec api alembic upgrade head

logs:
    docker compose logs -f api

seed:
    docker compose exec api python scripts/seed_events.py

test:
    docker compose exec api pytest -v

test-rules:
    docker compose exec api pytest -v tests/test_rules.py tests/test_rule_engine.py

test-playbooks:
    docker compose exec api pytest -v tests/test_playbooks.py

test-api:
    docker compose exec api pytest tests/test_alerts.py -v

watch-alerts:
    curl -N http://localhost:8000/api/v1/alerts/stream

# Manually watch the live alert feed from your terminal
watch-alerts:
    curl -N http://localhost:8000/api/v1/alerts/stream