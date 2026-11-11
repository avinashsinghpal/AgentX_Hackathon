from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now
from app.db.types import JSONType

if TYPE_CHECKING:
    pass


class PolicyEvaluation(Base):
    """Immutable record of one deterministic policy evaluation.

    Re-evaluating a case appends a new row; old rows are never overwritten so the
    exact policy version and inputs behind a historical decision remain
    auditable.
    """

    __tablename__ = "policy_evaluations"
    __table_args__ = (
        Index("ix_policy_evaluations_case_id", "case_id"),
        Index("ix_policy_evaluations_case_evaluated", "case_id", "evaluated_at"),
        Index("ix_policy_evaluations_seller_policy_id", "seller_policy_id"),
        Index("ix_policy_evaluations_decision", "decision"),
    )

    case_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=True,
    )
    seller_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    seller_policy_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("seller_policies.id", ondelete="SET NULL"),
        nullable=True,
    )
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_result: Mapped[dict[str, Any]] = mapped_column(
        JSONType, default=dict, nullable=False
    )
    evaluator_version: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
