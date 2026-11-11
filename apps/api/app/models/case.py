from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.action import Action
    from app.models.buyer import Buyer
    from app.models.file_upload import FileUpload
    from app.models.order import Order
    from app.models.policy_evaluation import PolicyEvaluation
    from app.models.seller import Seller


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        # A case and its order must belong to the same seller.  Independent
        # foreign keys alone would allow a cross-tenant case.
        ForeignKeyConstraint(
            ["seller_id", "order_id"],
            ["orders.seller_id", "orders.id"],
            name="fk_cases_seller_order",
            ondelete="CASCADE",
        ),
        Index("ix_cases_seller_order", "seller_id", "order_id"),
    )

    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    buyer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("buyers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    case_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="open",
        nullable=False,
        index=True,
    )  # "open" | "investigating" | "pending_approval" | "resolved" | "rejected"
    issue_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # "damaged" | "missing_item" | "delay" | "wrong_item" | "defective" | "cancellation"
    customer_narrative: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # Deprecated compatibility projection of the evidence attached to this case.
    # ``file_uploads.case_id`` is the authoritative association; see
    # app.services.evidence.
    evidence_urls: Mapped[list[str]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )  # list of uploaded file IDs / paths
    # UI compatibility badge: "executed" | "needs_approval" | "not_eligible".
    # The real policy decision is stored in policy_evaluations.decision; an action
    # outcome is not a policy decision and is never written here by the evaluator.
    decision: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    outcome_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    resolution_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )  # "refund" | "return_label" | "replacement" | "explanation" | "delay_compensation"
    approved_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="cases")
    buyer: Mapped["Buyer"] = relationship("Buyer", back_populates="cases")
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="cases",
        foreign_keys=[order_id],
    )
    messages: Mapped[list["CaseMessage"]] = relationship(
        "CaseMessage",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseMessage.created_at",
    )
    approvals: Mapped[list["ApprovalRequest"]] = relationship(
        "ApprovalRequest",
        back_populates="case",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["FileUpload"]] = relationship(
        "FileUpload",
        back_populates="case",
    )
    actions: Mapped[list["Action"]] = relationship("Action", back_populates="case")
    policy_evaluations: Mapped[list["PolicyEvaluation"]] = relationship(
        "PolicyEvaluation",
        cascade="all, delete-orphan",
    )


class ApprovalRequest(Base):
    """Seller authorization request.

    Approval authorizes execution; it never proves execution.  The linked
    ``actions`` row is the only evidence that a financial operation happened.
    """

    __tablename__ = "approval_requests"
    __table_args__ = (Index("ix_approval_requests_seller_status", "seller_id", "status"),)

    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    policy_evaluation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("policy_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    auto_evaluation_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
    )
    requested_action: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
    )
    requested_amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # "pending" | "approved" | "rejected" | "expired" | "cancelled"
    seller_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    case: Mapped["Case"] = relationship("Case", back_populates="approvals")
    seller: Mapped["Seller"] = relationship("Seller", back_populates="approval_requests")


class CaseMessage(Base):
    __tablename__ = "case_messages"

    case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sender_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # "buyer" | "agent" | "seller"
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONType,
        nullable=True,
    )  # list of {tool_name, tool_args, outcome, timestamp}
    decision_badge: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )  # "executed" | "needs_approval" | "not_eligible"

    case: Mapped["Case"] = relationship("Case", back_populates="messages")
