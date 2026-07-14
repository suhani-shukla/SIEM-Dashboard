"""
FILE LOCATION: backend/app/models/alert_history.py

Alert lifecycle audit trail.

ASSUMPTION: your existing app/models/alert.py defines an `Alert` model with at
least these columns (from the Phase 2/3 spec):
    id (UUID pk), rule_name (str), mitre_technique (str), severity (str),
    triggered_at (datetime), matched_event_ids (JSONB list of UUIDs),
    summary (str), entity (str), status (str), created_at, updated_at

If your actual column names differ (e.g. `mitre_technique_id` instead of
`mitre_technique`), just adjust the join field names in services/alerts.py
— nothing here in this file depends on those names directly.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Optional: only works if your Alert model has `history = relationship(...)`
    # back_populates set up on the other side. Safe to remove this line if not.
    # alert = relationship("Alert", backref="history")

    def __repr__(self) -> str:
        return f"<AlertHistory alert_id={self.alert_id} {self.from_status}->{self.to_status}>"