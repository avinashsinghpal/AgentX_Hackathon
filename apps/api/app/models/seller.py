from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case import ApprovalRequest, Case
    from app.models.order import Order
    from app.models.user import User


class Seller(Base):
    __tablename__ = "sellers"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    store_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    store_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="onboarding",
        nullable=False,
        index=True,
    )  # "onboarding" | "active" | "suspended"
    onboarding_step: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="seller")
    operations: Mapped[Optional["SellerOperations"]] = relationship(
        "SellerOperations",
        back_populates="seller",
        uselist=False,
        cascade="all, delete-orphan",
    )
    policies: Mapped[list["SellerPolicy"]] = relationship(
        "SellerPolicy",
        back_populates="seller",
        cascade="all, delete-orphan",
        order_by="desc(SellerPolicy.version)",
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="seller",
        cascade="all, delete-orphan",
    )
    cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="seller",
        cascade="all, delete-orphan",
    )
    customer_links: Mapped[list["SellerCustomerLink"]] = relationship(
        "SellerCustomerLink",
        back_populates="seller",
        cascade="all, delete-orphan",
    )
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(
        "ApprovalRequest",
        back_populates="seller",
        cascade="all, delete-orphan",
    )


class SellerOperations(Base):
    __tablename__ = "seller_operations"

    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    warehouse_pincodes: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )  # list of PIN strings
    serviceable_pincodes: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["*"],
        nullable=False,
    )  # list of PIN strings or ["*"] for nationwide
    courier_partners: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["Delhivery", "Bluedart", "Shadowfax"],
        nullable=False,
    )
    cod_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    support_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    support_phone: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    business_hours: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="operations")


class SellerPolicy(Base):
    __tablename__ = "seller_policies"

    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    policy_yaml: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    parsed_rules: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="policies")


class SellerCustomerLink(Base):
    __tablename__ = "seller_customer_links"

    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    buyer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("buyers.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    invite_token: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=True,
    )
    invite_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )  # "pending" | "accepted" | "expired"
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="customer_links")
