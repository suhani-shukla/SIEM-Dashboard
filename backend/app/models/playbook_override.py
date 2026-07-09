from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base

class PlaybookOverride(Base):
    __tablename__ = "playbook_overrides"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
