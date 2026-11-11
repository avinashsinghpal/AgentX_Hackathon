from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now
from app.db.types import JSONType

if TYPE_CHECKING:
    from app.models.shipment import Shipment


class TrackingEvent(Base):
    """Normalized shipment tracking event.

    Authoritative tracking history.  ``shipments.tracking_events`` is retained
    as a legacy snapshot maintained by ``app.services.orders.sync_tracking_events``.
    """

    __tablename__ = "tracking_events"
    __table_args__ = (
        Index("ix_tracking_events_shipment_timestamp", "shipment_id", "event_timestamp"),
        # A provider event id is only unique where a provider actually supplies
        # one; events without an id are allowed to repeat (e.g. repeated scans).
        Index(
            "uq_tracking_events_shipment_provider_event",
            "shipment_id",
            "provider_event_id",
            unique=True,
            postgresql_where=text("provider_event_id IS NOT NULL"),
            sqlite_where=text("provider_event_id IS NOT NULL"),
        ),
    )

    shipment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="tracking_event_rows")

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.event_timestamp.isoformat(),
            "location": self.location,
            "status": self.status,
            "description": self.description,
        }
