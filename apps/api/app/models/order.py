from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.action import Action
    from app.models.buyer import Buyer
    from app.models.case import Case
    from app.models.order_item import OrderItem
    from app.models.seller import Seller
    from app.models.shipment import Shipment


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # One order number per seller (order numbers are only unique per tenant).
        UniqueConstraint("seller_id", "order_number", name="uq_orders_seller_order_number"),
        # Required as the parent key of the composite case -> order foreign key.
        UniqueConstraint("id", "seller_id", name="uq_orders_id_seller_id"),
    )

    seller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    buyer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("buyers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    order_number: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )
    total_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )  # Amount in minor units (paise, e.g. 149900 = INR 1499.00)
    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # "prepaid" | "cod"
    payment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # "captured" | "cod_pending" | "refunded" | "partially_refunded"
    order_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # "placed" | "shipped" | "delivered" | "cancelled" | "returned"
    shipping_address: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
    )
    # Legacy JSON snapshot of the order lines.  ``order_items`` is authoritative;
    # this column is written only by app.services.orders.sync_order_items and is
    # returned to clients for backward compatibility.
    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType,
        nullable=False,
    )  # list of {sku, title, quantity, unit_price, returnable}

    seller: Mapped["Seller"] = relationship("Seller", back_populates="orders")
    buyer: Mapped[Optional["Buyer"]] = relationship("Buyer", back_populates="orders")
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.created_at",
    )
    shipments: Mapped[list["Shipment"]] = relationship(
        "Shipment",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="order",
        cascade="all, delete-orphan",
        foreign_keys="Case.order_id",
    )
    actions: Mapped[list["Action"]] = relationship("Action", back_populates="order")
