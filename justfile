# SIEM Dashboard — development commands

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
