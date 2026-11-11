from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.tracking_event import TrackingEvent


class Shipment(Base):
    __tablename__ = "shipments"

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    courier_partner: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    tracking_number: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    awb: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    dispatch_pincode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    destination_pincode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    promised_delivery_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_delivery_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # "manifested" | "in_transit" | "out_for_delivery" | "delivered" | "failed_attempt" | "delayed"
    # Legacy JSON snapshot; ``tracking_events`` rows are authoritative.  Written
    # only by app.services.orders.sync_tracking_events.
    tracking_events: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType,
        default=list,
        nullable=False,
    )  # list of {timestamp, location, status, description}

    order: Mapped["Order"] = relationship("Order", back_populates="shipments")
    tracking_event_rows: Mapped[list["TrackingEvent"]] = relationship(
        "TrackingEvent",
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="TrackingEvent.event_timestamp",
    )
