"""
FILE LOCATION: backend/alembic/versions/003_alert_history.py

add alert_history table

Revision ID: 003_alert_history
Revises: 464a52720de3
Create Date: 2026-07-09

NOTE: set `down_revision` below to whatever your actual latest revision id is
(looks like it should be '464a52720de3_add_playbook_overrides_table' based on
your file tree — confirm with `alembic heads` before running).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_alert_history"
down_revision = "464a52720de3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by", sa.String(length=128), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_history_alert_id", "alert_history", ["alert_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_history_alert_id", table_name="alert_history")
    op.drop_table("alert_history")