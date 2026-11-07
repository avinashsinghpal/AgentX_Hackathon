from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.buyer import Buyer
    from app.models.file_upload import FileUpload
    from app.models.order import Order
    from app.models.seller import Seller


class Case(Base):
    __tablename__ = "cases"

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
    evidence_urls: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )  # list of uploaded file IDs / paths
    decision: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )  # "executed" | "needs_approval" | "not_eligible"
    outcome_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    resolution_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )  # "refund" | "return_label" | "replacement" | "explanation"
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
    order: Mapped["Order"] = relationship("Order", back_populates="cases")
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


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

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
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    auto_evaluation_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    requested_action: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # "pending" | "approved" | "rejected"
    seller_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
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
        JSON,
        nullable=True,
    )  # list of {tool_name, tool_args, outcome, timestamp}
    decision_badge: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )  # "executed" | "needs_approval" | "not_eligible"

    case: Mapped["Case"] = relationship("Case", back_populates="messages")
