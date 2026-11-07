from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class AuditLog(Base):
    __tablename__ = "audit_logs"

    seller_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    case_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    actor_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # "buyer" | "seller" | "agent" | "system"
    action: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    prev_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    current_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )
