# app/db/base.py
# This file's only job is to import all models so their tables register
# on Base.metadata — used by Alembic autogenerate and app startup.
from app.db.base_class import Base  # noqa
from app.models.alert import Alert  # noqa
from app.models.alert_history import AlertHistory  # noqa
from app.models.event import Event  # noqa
# ...import every other model here too