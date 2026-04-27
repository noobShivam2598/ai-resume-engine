from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AppliedStatus(str, Enum):
    NOT_APPLIED = "not_applied"
    APPLIED = "applied"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_url: Mapped[str] = mapped_column(Text, nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    applied_status: Mapped[AppliedStatus] = mapped_column(
        SAEnum(AppliedStatus),
        nullable=False,
        default=AppliedStatus.NOT_APPLIED,
        server_default=AppliedStatus.NOT_APPLIED.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="jobs")
