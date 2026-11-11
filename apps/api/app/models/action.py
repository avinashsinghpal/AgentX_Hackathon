from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.order import Order


ACTION_STATUSES = (
    "pending",
    "submitted",
    "verification_pending",
    "succeeded",
    "failed",
    "cancelled",
)

VERIFICATION_STATUSES = ("verified", "failed", "timeout", "pending")


class Action(Base):
    """A durable operational action (refund, wallet credit, return label).

    An action is never considered completed because a request was sent: only a
    recorded successful verification moves it to ``succeeded`` and only then is
    the order/case state updated.
    """

    __tablename__ = "actions"
    __table_args__ = (
        UniqueConstraint("seller_id", "idempotency_key", name="uq_actions_seller_idempotency"),
        CheckConstraint(
            "amount_minor IS NULL OR amount_minor >= 0",
            name="ck_actions_amount_non_negative",
        ),
        Index("ix_actions_case_id", "case_id"),
        Index("ix_actions_order_id", "order_id"),
        Index("ix_actions_status", "status"),
        Index("ix_actions_action_type", "action_type"),
    )

    case_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    order_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    initiated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["Case | None"] = relationship("Case", back_populates="actions")
    order: Mapped["Order | None"] = relationship("Order", back_populates="actions")
    verifications: Mapped[list["ActionVerification"]] = relationship(
        "ActionVerification",
        back_populates="action",
        cascade="all, delete-orphan",
        order_by="ActionVerification.verification_attempt",
    )


class ActionVerification(Base):
    """One verification attempt for an action (failures are retained)."""

    __tablename__ = "action_verifications"
    __table_args__ = (
        Index("ix_action_verifications_action_id", "action_id"),
        Index("ix_action_verifications_status", "verification_status"),
    )

    action_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_method: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_response: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    verification_attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    action: Mapped["Action"] = relationship("Action", back_populates="verifications")
