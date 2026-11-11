from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now
from app.db.types import JSONType

GLOBAL_CHAIN_KEY = "__global__"


class AuditLog(Base):
    """A node in a per-seller tamper-evident hash chain.

    The hash chain makes silent modification detectable; it is not intrinsically
    immutable.  A privileged database operator who rewrites rows and recomputes
    every later hash (and the chain-head row) is not detectable without an
    external checkpoint or independently stored anchor.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        UniqueConstraint("chain_key", "sequence", name="uq_audit_logs_chain_sequence"),
    )

    seller_id: Mapped[str | None] = mapped_column(
        String(36),
        index=True,
        nullable=True,
    )
    chain_key: Mapped[str] = mapped_column(
        String(36),
        default=GLOBAL_CHAIN_KEY,
        index=True,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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
        JSONType,
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


class AuditChainState(Base):
    """Locked chain head used to serialize concurrent appends per seller."""

    __tablename__ = "audit_chain_state"

    chain_key: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    last_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
